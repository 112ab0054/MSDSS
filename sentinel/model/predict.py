"""載入可搬移的模型，將請求 JSON 轉為預測類別與機率。"""
import argparse
import json
import hashlib
import numpy as np
from pathlib import Path

from xgboost import XGBClassifier
from features import LABELS, VERSION, features, feature_count, layout
from request_input import INPUT_VERSION
import request_input


class Predictor:
    """啟動服務時載入一次，之後重用同一物件處理多筆請求。

    model.json 保存樹模型；metadata.json 保存特徵版本與類別順序。
    兩者須一起搬移，並搭配對應版本的 features.py。
    """
    def __init__(self, directory=None):
        # 預設從本程式旁的 artifacts 找模型，不依賴執行指令時的工作目錄。
        """輸入 directory：完整推論套件的資料夾，可為 Path、字串或 None。
        None 時先找本程式旁的 model.json；沒有則找旁邊的 artifacts/，不以訓練機的路徑定位。
        明確傳相對路徑時，仍以目前工作目錄為準；整包搬機器後可直接改傳新的目錄。

        初始化的檢查順序：
        1. 讀 bundle-manifest.json，要求必要模型／程式／探針檔案都在清單內。
        2. 檢查每個檔名及 SHA-256，避免漏檔、內容被改或混入另一版檔案。
        3. 檢查 Python 實際 import 的 predict/features/request_input 也來自同版內容。
        4. 讀 metadata，核對套件版本、輸入版本、特徵版本、類別順序及 header 維度。
        5. 載入 model.json，確認樹模型期待的特徵數也相同。

        主要屬性：self.model 是記憶體中的樹模型；self.header_names 是固定槽位順序。
        self.feature_count 是模型需要的向量長度；self.exploratory 表示是否探索性訓練。
        self.mode 記錄 live/offline，舊檔沒有該欄時顯示 unspecified。
        載入失敗會拋例外，不回傳一個看似正常但無法正確預測的物件。
        SHA 檢查包含程式註解；要修改套件程式，須用可信來源重新產生一致套件，不能混用舊清單。

        v5 額外核對 feature_layout，包含 4 通道、512 雜湊桶、2～5 字元 n-gram 等設定。
        即使兩套特徵剛好長度一樣，計算布局不同也必須拒絕；只核對維度不足以保證相容。
        當文件 header 有 12 種時，feature_count(...) 是 2402；不再使用舊版 74+17×N 當完整維度。
        """
        here = Path(__file__).resolve().parent
        directory = Path(directory) if directory else (here if (here / 'model.json').is_file() else here / 'artifacts')
        self.directory = directory.resolve()
        # 先核對套件檔名與內容，再讀模型；SHA 只證明一致，沒有簽章就不能證明發布者可信。
        manifest = json.loads((directory / 'bundle-manifest.json').read_text(encoding='utf-8'))
        if not {'model.json', 'metadata.json', 'features.py', 'request_input.py', 'predict.py', 'self-test.json'} <= set(manifest):
            raise ValueError('模型套件清單不完整')
        for name, expected in manifest.items():
            if Path(name).name != name or '/' in name or '\\' in name:
                raise ValueError('模型套件含不合法路徑')
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                raise ValueError('模型套件檔案不一致：' + name)
        # 再確認 Python 真正 import 的程式，避免工作目錄內另一份 features.py 搶先被載入。
        for name, actual_file in [('predict.py', Path(__file__)),
                                   ('features.py', Path(features.__code__.co_filename)),
                                   ('request_input.py', Path(request_input.__file__))]:
            if hashlib.sha256(actual_file.read_bytes()).hexdigest() != manifest[name]:
                raise ValueError('目前載入的程式與模型套件不同：' + name)
        meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        # 特徵順序或類別順序不同就拒絕載入，避免產生錯誤預測。
        if (meta.get('bundle_version') != 1 or meta.get('request_input_version') != INPUT_VERSION
                or meta["feature_version"] != VERSION or meta["labels"] != LABELS):
            raise ValueError("模型與特徵程式版本不符")
        self.exploratory = meta["exploratory"]
        self.mode = meta.get('mode', 'unspecified')
        self.header_names = meta['header_names']
        self.feature_count = meta['feature_count']
        # 同時比對槽位排序、v5 維度及完整 layout，不能只以向量長度相同判定相容。
        if (self.header_names != sorted(set(self.header_names)) or self.feature_count != feature_count(self.header_names)
                or meta.get('feature_layout') != layout()):
            raise ValueError('Header 順序／維度不符')
        # 初始化只載入一次，後續重用；固定 CPU 避免部署依賴 CUDA。
        self.model = XGBClassifier()
        self.model.load_model(directory / "model.json")
        self.model.set_params(device='cpu', n_jobs=2)
        if self.model.get_booster().num_features() != self.feature_count:
            raise ValueError('模型實際特徵維度不符')

    def self_test(self):
        """輸入：不需額外參數，讀 self.directory/self-test.json。
        輸出：如 {'passed': True, 'probes': 3, 'exploratory': False}。
        每筆探針包含一個遮蔽後的 train 請求與原環境算出的三類機率。
        重新推論後以 np.allclose 比較，允許 atol/rtol 各 1e-6 的浮點誤差。

        若在 Colab 與 Linux 都通過，只表示這些探針的計算一致；不能據此保證所有輸入都相同。
        這也沒有真實標籤對照，因此不是準確率測試或泛化能力評估。
        無探針或結果不一致會拋 ValueError，讓部署者先處理環境／套件差異。
        """
        probes = json.loads((self.directory / 'self-test.json').read_text(encoding='utf-8'))
        if not probes:
            raise ValueError('套件缺少跨系統自我檢查樣本')
        for probe in probes:
            result = self.predict(probe['request'])
            actual = [result['probabilities'][label] for label in LABELS]
            if not np.allclose(actual, probe['probabilities'], atol=1e-6, rtol=1e-6):
                raise ValueError('目前環境的預測與訓練環境不一致')
        return {'passed': True, 'probes': len(probes), 'exploratory': self.exploratory}

    def predict(self, request):
        """將一筆請求轉為特徵，再取機率最高的類別。

        機率未經校準，0.9 不代表實際有 90% 正確率。
        exploratory 表示模型是否使用候選模式訓練，不應隱藏此標記。
        本版使用固定 argmax 規則，沒有依測試資料調整告警門檻。

        輸入 request：單筆請求字典，格式與訓練時 input 一致；不是包含 annotation 的整份樣本。
        輸出範例：{'label': 'sqli', 'mode': 'live', 'exploratory': False,
                   'probabilities': {'normal': 0.1, 'sqli': 0.8, 'xss': 0.1}}。
        以上數字僅為格式示例，不是目前模型的真實成績。

        vector 是 features 回傳的一維清單；[vector] 把它包成 XGBoost 要求的二維批次。
        predict_proba 結果為「1 筆 × 3 類」，取 [0] 得到單筆三類分數。
        argmax 回傳最大分數的欄位索引，再用 LABELS 還原類別字串。
        分數同分時 NumPy argmax 會取最前面的最大值，類別順序因此不能任意調換。
        這裡只回傳分類，不送 HTTP、不寫 log、不封鎖請求；是否採取動作由 gateway 決定。

        新版輸出還包含 mode，明確保留 live/offline 來源模式。
        offline 模型可能在分類題上高分，但此標記提醒它並未證明請求已送達真實平台。
        """
        vector = features(request, self.header_names)
        if len(vector) != self.feature_count:
            raise ValueError('模型與文件 header 特徵維度不符')
        # 單筆也包成 1×特徵數批次；[0] 取出三類分數，argmax 選最大欄位再查 LABELS。
        probabilities = self.model.predict_proba([vector])[0]
        return {"label": LABELS[int(probabilities.argmax())],
                'mode': self.mode,
                "exploratory": self.exploratory,
                "probabilities": dict(zip(LABELS, map(float, probabilities)))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, nargs='?')
    parser.add_argument("--model", type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    # 支援含 BOM 的 UTF-8 請求檔；不使用系統預設編碼。
    predictor = Predictor(args.model)
    if args.self_test:
        result = predictor.self_test()
    else:
        if args.request is None:
            parser.error('請提供 request.json 或 --self-test')
        request = json.loads(args.request.read_text(encoding="utf-8-sig"))
        result = predictor.predict(request)
    print(json.dumps(result, ensure_ascii=False))

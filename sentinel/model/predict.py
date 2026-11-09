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
        here = Path(__file__).resolve().parent
        directory = Path(directory) if directory else (here if (here / 'model.json').is_file() else here / 'artifacts')
        self.directory = directory.resolve()
        manifest = json.loads((directory / 'bundle-manifest.json').read_text(encoding='utf-8'))
        if not {'model.json', 'metadata.json', 'features.py', 'request_input.py', 'predict.py', 'self-test.json'} <= set(manifest):
            raise ValueError('模型套件清單不完整')
        for name, expected in manifest.items():
            if Path(name).name != name or '/' in name or '\\' in name:
                raise ValueError('模型套件含不合法路徑')
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                raise ValueError('模型套件檔案不一致：' + name)
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
        if (self.header_names != sorted(set(self.header_names)) or self.feature_count != feature_count(self.header_names)
                or meta.get('feature_layout') != layout()):
            raise ValueError('Header 順序／維度不符')
        self.model = XGBClassifier()
        self.model.load_model(directory / "model.json")
        self.model.set_params(device='cpu', n_jobs=2)
        if self.model.get_booster().num_features() != self.feature_count:
            raise ValueError('模型實際特徵維度不符')

    def self_test(self):
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
        """
        vector = features(request, self.header_names)
        if len(vector) != self.feature_count:
            raise ValueError('模型與文件 header 特徵維度不符')
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

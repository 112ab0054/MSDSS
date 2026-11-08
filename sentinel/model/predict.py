"""載入可搬移的模型，將請求 JSON 轉為預測類別與機率。"""
import argparse
import json
from pathlib import Path

from xgboost import XGBClassifier
from features import LABELS, VERSION, features


class Predictor:
    """啟動服務時載入一次，之後重用同一物件處理多筆請求。

    model.json 保存樹模型；metadata.json 保存特徵版本與類別順序。
    兩者須一起搬移，並搭配對應版本的 features.py。
    """
    def __init__(self, directory=None):
        # 預設從本程式旁的 artifacts 找模型，不依賴執行指令時的工作目錄。
        directory = Path(directory) if directory else Path(__file__).resolve().parent / "artifacts"
        meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        # 特徵順序或類別順序不同就拒絕載入，避免產生錯誤預測。
        if meta["feature_version"] != VERSION or meta["labels"] != LABELS:
            raise ValueError("模型與特徵程式版本不符")
        self.exploratory = meta["exploratory"]
        self.model = XGBClassifier()
        self.model.load_model(directory / "model.json")

    def predict(self, request):
        """將一筆請求轉為特徵，再取機率最高的類別。

        機率未經校準，0.9 不代表實際有 90% 正確率。
        exploratory 表示模型是否使用候選模式訓練，不應隱藏此標記。
        本版使用固定 argmax 規則，沒有依測試資料調整告警門檻。
        """
        probabilities = self.model.predict_proba([features(request)])[0]
        return {"label": LABELS[int(probabilities.argmax())],
                "exploratory": self.exploratory,
                "probabilities": dict(zip(LABELS, map(float, probabilities)))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--model", type=Path)
    args = parser.parse_args()
    # 支援含 BOM 的 UTF-8 請求檔；不使用系統預設編碼。
    request = json.loads(args.request.read_text(encoding="utf-8-sig"))
    print(json.dumps(Predictor(args.model).predict(request), ensure_ascii=False))

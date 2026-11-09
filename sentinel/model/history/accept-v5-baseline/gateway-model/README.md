# 可搬移推論套件

安裝 requirements-inference.txt，執行 `python predict.py --self-test --model .`。此路徑由命令明確提供；預設也會在 predict.py 旁尋找模型。模型以 XGBoost JSON 儲存，沒有 pickle 或訓練資料的絕對路徑。跨系統需實際執行 self-test；未經校準的機率不是正確率保證。

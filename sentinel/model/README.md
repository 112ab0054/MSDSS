# XGBoost 訓練與推論

目前資料集是sentinel/dataset/small-api-v9，共1098筆：train702、test150、validation150、challenge96。類別normal、sqli、xss固定；Bagisto／Shopware用於訓練與測試，Sylius結合httpParamsDataset payload作獨立驗證；Medusa不加入訓練資料。

目前部署模型是使用者提供的Colab v9，保存在sentinel/gateway/model完整套件；feature v6、request input v3、2402維。offline／exploratory標記如實保留。模型來源與指紋見[gateway MODEL](../gateway/MODEL.md)。

## 訓練

```sh
python -m pip install -r sentinel/model/requirements.txt
python sentinel/model/train.py --mode offline --check-only --data-dir sentinel/dataset/small-api-v9
python sentinel/model/train.py --mode offline --data-dir sentinel/dataset/small-api-v9 --output NEW_RUN_DIRECTORY
```

Colab使用[msdss訓練.ipynb](msdss訓練.ipynb)及dataset.zip。ZIP目前資料與v9一致；若修改訓練程式／資料後需重新打包，請使用新檔名：

```sh
python sentinel/model/prepare_colab.py --data-dir sentinel/dataset/small-api-v9 --output dataset_new.zip
```

## 輸出及推論

輸出包含inference.zip、模型套件、test／validation／challenge的report.json、report.md、逐筆預測CSV、混淆矩陣、ROC與PR資料及圖。指標含accuracy、balanced accuracy、各類precision／recall／F1、macro／weighted／micro F1、MCC、log loss、Brier、normal誤報率、攻擊偵測召回與漏報率；信賴區間受獨立群組數限制，不將離線分數當實機防護效果。

跨機器推論必須整包搬移模型與相同版本的predict.py、features.py、request_input.py、metadata.json、bundle-manifest.json及self-test.json，不能只搬model.json。保留.gitattributes中模型原始bytes規則，避免Git換行破壞SHA。推論不依賴Colab絕對路徑。

```sh
python sentinel/gateway/model/predict.py --self-test
```

最新版Colab評估保存在[results/colab-v9-2026-11-09](results/colab-v9-2026-11-09/)。gateway目前分析所有經過它的支援HTTP路徑，原77項清單僅供文件／平台驗證；模型忙碌時排隊。見[gateway README](../gateway/README.md)。

## 清理及測試

2026-11-10本機已移除舊資料集v1～v8、舊模型壓縮包及中間輸出。保留最新v9、完整部署模型、dataset.zip、Notebook、目前依賴的程式及來源／授權。舊版本比較測試移除；現用骨架、語義、憑證遮蔽、訓練／推論搬移與Git換行測試改為獨立驗證v9。

```sh
python -B -m unittest discover -s sentinel/model -p 'test_*.py'
```

清理不代表過去研究歷程消失，舊檔仍可從Git歷史還原；不會改寫v9原始請求或模型權重。保留的骨架解析器原始碼與SKELETON-PYTHON-LICENSE.txt是當前訓練前檢查的相依，不是可刪的舊版備份。

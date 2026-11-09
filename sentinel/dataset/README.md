# 目前資料集：small-api-v9

只保留最新版[small-api-v9](small-api-v9/README.md)，1098筆，三類normal／sqli／xss：train702、test150、validation150、challenge96。train與test來自Bagisto及Shopware，validation為Sylius結合httpParamsDataset payload；Medusa只作展示，不加入資料集。

這是離線生成資料，沒有宣稱全部HTTP實機執行。使用原始輸入，不以分組分析需要的骨架取代模型輸入。依三份API文件及資料庫選項填值，保留來源／授權、分組目錄與完整性指紋。詳見[參數語義與多樣性](../analysis/參數語義與資料多樣性v9.md)。

## 訓練與檢查

```sh
python sentinel/model/train.py --mode offline --check-only --data-dir sentinel/dataset/small-api-v9
python sentinel/model/train.py --mode offline --data-dir sentinel/dataset/small-api-v9 --output NEW_RUN_DIRECTORY
```

sentinel/model/dataset.zip已確認train.csv與v9完全一致，供Colab使用；Notebook在sentinel/model/msdss訓練.ipynb。整包推論模型在sentinel/gateway/model/，不是這個資料夾。

## 本機清理

2026-11-10已移除small-api-v1～v8、v6-annotated、live-small-api-v2及只適用舊版的比較測試／診斷輸出。當前模型測試改用v9，保留骨架防洩漏、輸入配對、資料語義、可搬移模型及Git換行完整性檢查。

保留evidence/、reference/、原始API文件、最新資料庫快照及授權來源。版本名稱的build程式中仍有目前測試／v9工具共用的函式，因此不因檔名帶版本就刪除。這些是程式碼，不是保留的舊資料集；舊生成鏈輸入如需重現，須從Git歷史還原，本機不再攜帶全部中間版本。

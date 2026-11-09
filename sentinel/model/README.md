# MSDSS：Colab 訓練與跨系統推論

目前版本：資料 small-api-v3、特徵 v5（2402 維）。使用 [msdss訓練.ipynb](msdss訓練.ipynb) 與 [dataset.zip](dataset.zip)，重新上傳 Colab 並從第一格執行。預設 offline，沒有人工審核門檻。這是離線生成請求分類，不宣稱平台已實測或攻擊成功。

## 資料配置

| 集合 | 平台 | normal/sqli/xss 各類 | 合計 | 用途 |
|---|---|---:|---:|---|
| train | Bagisto＋Shopware | 150 | 450 | 唯一參與模型 fit 的資料 |
| test | Bagisto＋Shopware | 50 | 150 | 已見家族、不同模板／API |
| validation | Sylius | 50 | 150 | 新抽樣 httpParamsDataset payload＋API |
| challenge | Bagisto＋Shopware | 32 | 96 | 保留的未見編碼／語境家族 |

主實驗仍是60/20/20；96筆挑戰資料另計，合計846筆，不使用Medusa。每類四位置約等量：train 38/38/37/37，test與validation 13/13/12/12，challenge各8。

三份人工 API 文件原文不改；62操作、620個「API＋位置＋欄位」皆有覆蓋。攻擊只替換文件宣告的非敏感欄位。正常字面程式碼內容只放搜尋／備註等合適自由文字欄，不放認證／語言／貨幣欄。詳細來源、限制、欄位與抽樣見 [資料說明](../dataset/small-api-v3/README.md)。

XSS 訓練有5家族、20種原文；一般test有相同5家族但10種不同模板。挑戰保留實體編碼、JS註解邊界等語境；這不是保證未知攻擊全覆蓋。Sylius外部輸入固定來源commit、固定種子，避開v2用過的原文，不依成績篩選。家族是請求字串／意圖分類，不冒充已完成反射型、儲存型或DOM瀏覽器測試。

## v5 特徵

保留v4的278維方法、Content-Type、原始query/body/path統計與12個文件Header個別區塊。另於query、body、path、非敏感Header四通道加入：

- 原始字元2–5 gram，各512個hash桶，不建立／擬合詞彙表。
- JS括號、花括號、反引號、美元符、註解等邊界；函式／物件存取及實體／百分比編碼字樣。
- 原文不解碼、不替換ID／Email、不改大小寫或空白，不作L2正規化。Header名稱按HTTP語意不分大小寫，值保持原樣。

採 [HashingVectorizer](https://scikit-learn.org/1.7/modules/generated/sklearn.feature_extraction.text.HashingVectorizer.html) 的 callable analyzer，避免內建char analyzer壓縮空白。hash不是Python隨機hash；設定與程式隨模型一起保存。hash桶仍可能碰撞，不宣稱完整語意辨識。

密碼、Token、Cookie、Key實值仍遮蔽；敏感Header只用存在資訊，不使用值或真實長度。現在 `${void(0)}` 與 `blue shirt` 在相同框架中會有不同特徵。舊v4模型不可用v5特徵推論；舊完整套件則保留自己版本的程式。

## Colab

1. 上傳新版 Notebook。
2. 第一格上傳新版 dataset.zip；舊v2包會被明確提示，避免混用。
3. 安裝套件，執行檢查、訓練、三份評估與下載。

本機使用同一套程式：

```sh
python -m pip install -r sentinel/model/requirements.txt
python sentinel/model/train.py --mode offline --data-dir sentinel/dataset/small-api-v3 --output NEW_RUN_DIRECTORY
```

重新打包（新檔名）：

```sh
python sentinel/model/prepare_colab.py --data-dir sentinel/dataset/small-api-v3 --output dataset_new.zip
```

程式使用明確分割、不重新洗牌。v3一般test允許相同家族，但原始攻擊字串、模板、操作與正常／攻擊配對不可跨集合；challenge家族不得出現在train/test。真實session、來源證據及原文重複也不得跨集合。歷史參考值不是實際session；不虛構已採集旗標。

固定150棵樹、深度3、learning_rate=.05、CPU、seed42。只fit train，不以test、validation或challenge early stopping／選參數。若要調參，只在train內另建分組開發流程；最終研究效果應保留新的未檢視資料。

`--mode live` 保留真實HTTP、session、v3原文、證據SHA／request ID／內容對帳。`--allow-candidates` 是舊的已送出流程試跑選項，不等於offline。人工核准、training_approved、reviewer等均不是訓練門檻，也不輸出manual_review_required欄位。

## 輸出數據

summary.md、experiment.json、split.csv保存實驗與分割；test/、validation/、challenge/分別保存：

- report.md／report.json：整體、逐類、逐平台成績及稽核。
- metrics.csv／per-class.csv：Accuracy、Precision、Recall、Macro／Weighted／Micro-F1、Specificity、FPR／FNR、攻擊召回／漏報率、MCC、Kappa、Log loss、Brier。
- confusion_matrix.csv與confusion_matrix_normalized.csv；列為真實、欄為預測。
- curves.csv：ROC／PR座標，report.json含逐類ROC-AUC、Average Precision；AP不混稱梯形PR-AUC。
- predictions.csv：樣本ID、群組、真實／預測及三類機率，不輸出原始請求。
- 多數類基準、相同特徵向量跨集合數、資料／程式SHA、版本、訓練時間、median/p95推論延遲。

Notebook只顯示一份比較表、逐類表和收合設定，各評估集一張三合一圖。完整檔案仍保留。群組不足20時不報信賴區間；相依群組不等於實際購物流程次數。機率尚未校準。

## Windows／Ubuntu 推論

將 inference.zip 整包解壓、一起保留。在解壓目錄：

```sh
python -m pip install -r requirements-inference.txt
python predict.py --self-test
python predict.py request.json
```

或從其他目錄指定predict.py完整路徑；模型預設由程式所在目錄定位，沒有C槽或/content的固定依賴。套件含XGBoost model.json、metadata.json、三份推論程式、實際訓練版本依賴、SHA清單與三類自測樣本，不使用pickle/joblib。

載入會核對特徵版本、完整layout、Header順序、實際維度、模型／程式SHA；自測比較訓練環境機率（容許誤差1e-6）。目前Windows的固定依賴、中文／空白搬移及解壓後自測已檢查，記錄見 [v3驗證](../dataset/small-api-v3/verification.json)。Colab／Ubuntu仍需在當地執行self-test，不能把Windows資料夾名稱模擬當成Linux實測。

## 基準保留

舊420筆small-api-v2不覆寫；[v4診斷](xss-audit-2026-11-09/report.md)與[舊套件／程式](history/xss-v4-baseline/README.md)保留。新資料與特徵同時改變，不能把新舊不同資料上的分數差直接當成單一特徵改善量。歷史正常證據亦不改寫；Medusa／Mirage／根compose未變更。

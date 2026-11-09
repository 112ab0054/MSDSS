# MSDSS：Colab 訓練與跨系統推論

目前版本：資料 small-api-v5、特徵 v5（2402 維）。使用 [msdss訓練.ipynb](msdss訓練.ipynb) 與 [dataset.zip](dataset.zip)，重新上傳 Colab 並從第一格執行。預設 offline，沒有人工審核門檻。這是離線生成請求分類，不宣稱平台已實測或攻擊成功。

## 資料配置

| 集合 | 平台 | normal/sqli/xss 各類 | 合計 | 用途 |
|---|---|---:|---:|---|
| train | Bagisto＋Shopware | 198 | 594 | 唯一參與模型 fit 的資料 |
| test | Bagisto＋Shopware | 50 | 150 | 不同骨架群／API |
| validation | Sylius | 50 | 150 | 新抽樣 httpParamsDataset payload＋API |
| challenge | Bagisto＋Shopware | 32 | 96 | 保留語境群與其近似變體 |

目前只增加train144筆，主實驗594/150/150，比例不再是60/20/20；challenge96另計，共990筆，不使用Medusa。新增每類四位置各12筆，保留集CSV與骨架完全不變。

三份人工 API 文件原文不改；62操作、620個「API＋位置＋欄位」皆有覆蓋。攻擊只替換文件宣告的非敏感欄位。正常字面程式碼內容只放搜尋／備註等合適自由文字欄，不放認證／語言／貨幣欄。詳細來源、限制、欄位與抽樣見 [資料說明](../dataset/small-api-v5/README.md)。

新版先以保守片段語法與近似原文建立全域骨架關聯，再分集合。字串／數字、console輸出別名、大小寫與常見編碼變體保守同組，正常對照依配對留在同集合。外部骨架保留Sylius驗證，本地重疊者排除；原challenge骨架與其兄弟保留challenge，其餘固定雜湊分配。家族可共享，骨架不可跨。規則不是完整SQL/JS解析器，不能保證所有語意近似都抓到。詳見 [骨架分組紀錄](../analysis/skeleton-split-v4.md)。

原始輸入不解碼、不重寫；分析視圖與分組欄位不進模型。舊 small-api-v3、原Notebook及ZIP保留於 history/xss-v3-baseline，作較容易的近似變體基準。舊97.33%不能當作新切分的結果。

v5訓練補強已新增24種無註解SQL原文、24種XSS原文與48筆文件允許的正常文字／公司名稱控制；48組配對共144筆，全部只進train。舊v4與可用於Python3.13的Notebook／ZIP保存在history/train-v4-baseline。新增案例先避開所有既有攻擊骨架與跨家族原文近似，保留集再以SHA核對凍結。沒有新增HTTP證據；詳見 [v5補強紀錄](../analysis/train-augmentation-v5.md)。

## v5 特徵

保留v4的278維方法、Content-Type、原始query/body/path統計與12個文件Header個別區塊。另於query、body、path、非敏感Header四通道加入：

- 原始字元2–5 gram，各512個hash桶，不建立／擬合詞彙表。
- JS括號、花括號、反引號、美元符、註解等邊界；函式／物件存取及實體／百分比編碼字樣。
- 原文不解碼、不替換ID／Email、不改大小寫或空白，不作L2正規化。Header名稱按HTTP語意不分大小寫，值保持原樣。

採 [HashingVectorizer](https://scikit-learn.org/1.7/modules/generated/sklearn.feature_extraction.text.HashingVectorizer.html) 的 callable analyzer，避免內建char analyzer壓縮空白。hash不是Python隨機hash；設定與程式隨模型一起保存。hash桶仍可能碰撞，不宣稱完整語意辨識。

密碼、Token、Cookie、Key實值仍遮蔽；敏感Header只用存在資訊，不使用值或真實長度。現在 `${void(0)}` 與 `blue shirt` 在相同框架中會有不同特徵。舊v4模型不可用v5特徵推論；舊完整套件則保留自己版本的程式。

## Colab

1. 上傳新版 Notebook。
2. 第一格上傳新版 dataset.zip；舊v2／v3包會被明確提示，避免混用。
3. 安裝套件，執行檢查、訓練、三份評估與下載。

本機使用同一套程式：

```sh
python -m pip install -r sentinel/model/requirements.txt
python sentinel/model/train.py --mode offline --data-dir sentinel/dataset/small-api-v5 --output NEW_RUN_DIRECTORY
```

重新打包（新檔名）：

```sh
python sentinel/model/prepare_colab.py --data-dir sentinel/dataset/small-api-v5 --output dataset_new.zip
```

程式使用明確分割、不重新洗牌。v4允許家族共享，但骨架群、原始攻擊字串、模板、操作與正常／攻擊配對不可跨集合；訓練前重算目錄及實際資料，不只信任ID。challenge是保留語境群，不宣稱家族完全未見。真實session、來源證據及原文重複也不得跨集合。歷史參考值不是實際session；不虛構已採集旗標。

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

載入會核對特徵版本、完整layout、Header順序、實際維度、模型／程式SHA；自測比較訓練環境機率（容許誤差1e-6）。目前Windows的固定依賴、中文／空白搬移及解壓後自測已檢查，記錄見 [v5驗證](../dataset/small-api-v5/verification.json)。Colab／Ubuntu仍需在當地執行self-test，不能把Windows資料夾名稱模擬當成Linux實測。

## 基準保留

舊420筆small-api-v2不覆寫；[v4診斷](xss-audit-2026-11-09/report.md)與[舊套件／程式](history/xss-v4-baseline/README.md)保留。新資料與特徵同時改變，不能把新舊不同資料上的分數差直接當成單一特徵改善量。歷史正常證據亦不改寫；Medusa／Mirage／根compose未變更。

## Python 3.13 骨架重算修正

若遇到「骨架目錄無法由原文重算」，此次原因為 Python 標準庫 HTMLParser 在3.11與3.13對不完整註解／CDATA片段的處理不同。本版把 CPython3.11.3 的 HTMLParser 與其 markupbase 依 PSF 授權保存為專用模組，使用版本ID與檔案SHA核對。沒有關閉洩漏檢查、沒有接受錯誤目錄，也沒有正規化模型輸入。

全部846筆與CSV、骨架ID和集合配置保持原樣。107筆骨架目錄與846筆樣本已在Python3.11.3及3.13.13重算一致，跨集合篡改仍會被攔截。這是Windows兩個Python版本的驗證，不冒充已在Colab／Linux服務上實測。細節見 ../dataset/small-api-v4/parser-compatibility.json。

重新上傳最新dataset.zip，並從Notebook第一格重新解壓；只重跑檢查格會繼續使用Colab內的舊程式。解析器與授權檔會隨ZIP攜帶，推論特徵與模型格式不變。

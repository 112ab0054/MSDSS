# MSDSS：Colab 訓練與跨系統推論

後續補證：密碼重設HTTP已確認產生新Token並使舊Token失效；搜尋可用GET /store/products?q=...；付款可透過建立API替換session（ID會改變）。原79操作分類仍為60／1／7／11，累計357筆HTTP與實際分數匹配、193項業務斷言通過。 [補證與替代API](../analysis/Medusa剩餘項目再補證與替代API.md)。下列先前累計數字屬歷史輪次。

最新補資料實測：60成功、1部分成功、7前置不足、11版本／功能差異，not_run=0；339筆HTTP與實際gateway分數匹配，184項業務斷言通過。促銷、四種目錄明細、密碼更新、退貨及通用驗證碼已補通；通知／郵件送達仍未驗證。 [本輪實測紀錄](../analysis/Medusa補測資料建立與驗收.md)


最新Medusa狀態（依原文件復核後）：79項均有HTTP紀錄，not_run=0；60成功、1部分成功、7前置不足、11版本／功能差異。Cookie成功限真正HTTPS；移轉接受／拒絕使用原生token、通知送達未測。配送500保留，但已證實manual不支援動態計價，改列前置不足。[最新逐項補測](../analysis/Medusa剩餘API補測與runtime同步.md)。下文42成功／29未測屬第一輪歷史。


最新模型：已接收使用者Colab v9輸出，更新gateway完整推論套件與inference-v9.zip；原v7套件保留。真實Medusa正常購物與離線建單完成，58筆正常意圖有3筆誤判，79操作中42項成功，其他狀態另列。[教授展示驗證與啟動方式](../analysis/Medusa教授展示驗證v9.md)。下文「gateway仍v7／尚未重訓」為之前資料修正階段的歷史紀錄。

目前版本：資料 small-api-v9（依資料庫與參數含意多樣化，含攻擊面向欄）、特徵 v6（2402 維）。使用 [msdss訓練.ipynb](msdss訓練.ipynb) 與 [dataset.zip](dataset.zip)，重新上傳 Colab 並從第一格執行。預設 offline，沒有人工審核門檻。這是離線生成請求分類，不宣稱平台已實測或攻擊成功。

## 資料配置

| 集合 | 平台 | normal/sqli/xss 各類 | 合計 | 用途 |
|---|---|---:|---:|---|
| train | Bagisto＋Shopware | 234 | 702 | 唯一參與模型 fit 的資料 |
| test | Bagisto＋Shopware | 50 | 150 | 不同骨架群／API |
| validation | Sylius | 50 | 150 | 新抽樣 httpParamsDataset payload＋API |
| challenge | Bagisto＋Shopware | 32 | 96 | 保留語境群與其近似變體 |

v5之後另增加train108筆傳輸header配對，主實驗702/150/150，比例不是60/20/20；challenge96另計，共1098筆，不使用Medusa。新增每類四位置各12筆，保留集CSV與骨架完全不變。

三份人工 API 文件原文不改；62操作、620個「API＋位置＋欄位」皆有狀態紀錄，選填／未綁定者有原因。攻擊只替換文件宣告的非敏感欄位。正常字面程式碼內容只放搜尋／備註等合適自由文字欄，不放認證／語言／貨幣欄。詳細來源、限制、欄位與抽樣見 [資料說明](../dataset/small-api-v9/README.md)。

新版先以保守片段語法與近似原文建立全域骨架關聯，再分集合。字串／數字、console輸出別名、大小寫與常見編碼變體保守同組，正常對照依配對留在同集合。外部骨架保留Sylius驗證，本地重疊者排除；原challenge骨架與其兄弟保留challenge，其餘固定雜湊分配。家族可共享，骨架不可跨。規則不是完整SQL/JS解析器，不能保證所有語意近似都抓到。詳見 [骨架分組紀錄](../analysis/skeleton-split-v4.md)。

原始輸入不解碼、不重寫；分析視圖與分組欄位不進模型。舊 small-api-v3、原Notebook及ZIP保留於 history/xss-v3-baseline，作較容易的近似變體基準。舊97.33%不能當作新切分的結果。

v5訓練補強已新增24種無註解SQL原文、24種XSS原文與48筆文件允許的正常文字／公司名稱控制；48組配對共144筆，全部只進train。舊v4與可用於Python3.13的Notebook／ZIP保存在history/train-v4-baseline。新增案例先避開所有既有攻擊骨架與跨家族原文近似，保留集再以SHA核對凍結。沒有新增HTTP證據；詳見 [v5補強紀錄](../analysis/train-augmentation-v5.md)。

目前v6修正Accept合法媒體型別萬用字元被當SQL註解的問題；只改該統計的語意，raw header、長度、符號與ngram不變。三類對稱補入正常傳輸header profile，原Medusa樣本不進train，保留CSV不變。總歷程與實測取捨見 [白話紀錄](../analysis/訓練版本與問題處理白話紀錄.md)。舊v5完整套件保存在history/accept-v5-baseline，不能搭配v6程式載入。

## v6 特徵（延續v5布局）

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
python sentinel/model/train.py --mode offline --data-dir sentinel/dataset/small-api-v9 --output NEW_RUN_DIRECTORY
```

重新打包（新檔名）：

```sh
python sentinel/model/prepare_colab.py --data-dir sentinel/dataset/small-api-v9 --output dataset_new.zip
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

載入會核對特徵版本、完整layout、Header順序、實際維度、模型／程式SHA；自測比較訓練環境機率（容許誤差1e-6）。目前Windows的固定依賴、中文／空白搬移及解壓後自測已檢查，記錄見 [v6驗證](../dataset/small-api-v6/verification.json)。Colab／Ubuntu仍需在當地執行self-test，不能把Windows資料夾名稱模擬當成Linux實測。

## 基準保留

舊420筆small-api-v2不覆寫；[v4診斷](xss-audit-2026-11-09/report.md)與[舊套件／程式](history/xss-v4-baseline/README.md)保留。新資料與特徵同時改變，不能把新舊不同資料上的分數差直接當成單一特徵改善量。歷史正常證據亦不改寫；Medusa／Mirage／根compose未變更。

## Python 3.13 骨架重算修正

若遇到「骨架目錄無法由原文重算」，此次原因為 Python 標準庫 HTMLParser 在3.11與3.13對不完整註解／CDATA片段的處理不同。本版把 CPython3.11.3 的 HTMLParser 與其 markupbase 依 PSF 授權保存為專用模組，使用版本ID與檔案SHA核對。沒有關閉洩漏檢查、沒有接受錯誤目錄，也沒有正規化模型輸入。

全部846筆與CSV、骨架ID和集合配置保持原樣。107筆骨架目錄與846筆樣本已在Python3.11.3及3.13.13重算一致，跨集合篡改仍會被攔截。這是Windows兩個Python版本的驗證，不冒充已在Colab／Linux服務上實測。細節見 ../dataset/small-api-v4/parser-compatibility.json。

重新上傳最新dataset.zip，並從Notebook第一格重新解壓；只重跑檢查格會繼續使用Colab內的舊程式。解析器與授權檔會隨ZIP攜帶，推論特徵與模型格式不變。

CSV新增「攻擊面向」顯示欄，多標籤以「；」分隔，normal為不適用。面向是可見語法與既有family的輔助判讀，不是攻擊成功證據。訓練仍只讀完整紀錄JSON，欄位不作模型輸入；原v6檔案保留，來源SHA與閱讀版SHA分開記錄，不需重訓。規則與計數見dataset/small-api-v6-annotated/attack-facets-rules.json。

資料v7依文件修正normal格式與語義，含111筆真實歷史語言ID、不同正常文字與正確壓縮criteria；未綁定的選填值另記省略原因，592個文件位置在normal出現，不能宣稱620全填。特徵仍v6，但權重已按新資料重訓；gateway與inference-v7.zip為新版，舊v6套件存history/document-values-before。完整歷程見白話紀錄，當前結果不再沿用舊資料分數。


## v8：實機語言值

Shopware 6.7.15.1 已查得英文與德文，逐個以語言header查context，確認實際語言鏈與locale。111筆normal分成英文54、德文57，配對的攻擊資料同步背景語言，攻擊目標是語言本身時保留原攻擊。共145筆請求輸入改變，1098筆總數與骨架／切分不變；Sylius validation CSV bytes不變。

當前Colab ZIP與Notebook已用v8，舊v7套件保存在history/language-v7-baseline。訓練程式／特徵／模型參數沿用，檢查程式新增語言證據驗證。**需重新上傳dataset.zip並訓練；gateway與inference-v7仍是舊v7模型，本次未覆蓋權重。** 語言查詢成功不代表整批資料已實機送出。


## v9：依參數含意多樣化

當前ZIP、Notebook與預設資料集用small-api-v9。依使用者要求只查既有Bagisto／Sylius資料庫，不部署應用。Bagisto資料庫只有en；Sylius8種語言都入離線目錄範圍資料，但目前通路只分配en_US，不能稱全部HTTP可用。國家、城市、郵遞區號、州省及巢狀地址同步產生；公司、人名、電話、搜尋、備註等按含意多樣化。有至少3筆的語義自由文字欄位皆至少3種值；少量欄位不複製湊數。1098筆、標籤、切分與攻擊骨架保留，1036筆欄位修正紀錄、794筆input改變。

所有集合含明確填值修正，須重新訓練，不能沿用v8分數。gateway與inference-v7權重未改。完整數量與範圍見[參數語義紀錄](../analysis/參數語義與資料多樣性v9.md)，逐欄計數見small-api-v9/free-text-diversity.csv。

最新[依原API文件逐項復核32項](../analysis/Medusa依原API文件逐項復核.md)，包含原文件快照、參數檢查、設定／資料庫／原生實作證據與HTTPS補測。未修改原API文件或模型。

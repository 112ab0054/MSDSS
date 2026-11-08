# XGBoost 基準模型

以 Bagisto、Shopware 訓練，Sylius 作最終測試；同一 session、正常對照配對與重複群不可跨集合。允許相同攻擊家族，這不是未知家族實驗。訓練側另外保留獨立 validation 做 early stopping，測試平台不參與選模型。

需要 Python 3.11–3.13，建議 3.12。以下指令在儲存庫根目錄執行，Windows 與 Linux 均適用：

```sh
python -m venv .venv
```

Windows 使用 `.venv\Scripts\python`，Linux 使用 `.venv/bin/python`；或啟用虛擬環境後，執行：

```sh
python -m pip install -r sentinel/model/requirements.txt
python sentinel/model/train.py candidates.csv --test-platform sylius
python sentinel/model/predict.py request.json
```

輸入支援候選 CSV（`完整紀錄JSON` 欄位）與正式審核工具匯出的 JSONL。正式訓練僅接受 metadata.training_approved 為 JSON true 的資料；人工審核後請將最終標籤寫入 annotation.label（未提供時使用 proposed_label）。不要為了跑程式而批次核准候選。

目前 260 筆皆未審核，正式訓練會停止。只想檢查流程可使用 `--allow-candidates --output scratch-model`，結果不代表正式模型。即使試跑，缺少獨立三類資料時仍會停止，需補採獨立 session，不能強行拆列。

預設輸出至程式旁的 artifacts，可用 --output 改位置。包含 model.json、metadata.json 與 report.json。報告有各類 precision/recall/F1、Macro-F1 與混淆矩陣（順序 normal、sqli、xss）。

## 搬到 Linux 推論

複製 `features.py`、`predict.py`、`requirements.txt` 與整個 `artifacts/` 資料夾到任意位置。在 Linux 重新建立虛擬環境並安裝依賴；不要複製 Windows 的 .venv。推論預設由 `__file__` 找模型，不依賴目前工作目錄，也不保存訓練 CSV 的絕對路徑。指定其他模型使用 `--model /path/to/artifacts`。

request.json 範例：

```json
{"method":"GET","path":"/products","query":{"q":["shirt"]},"headers":{},"body":null}
```

輸出為 label 與三類機率；機率尚未校準。

## 範圍與驗證

這是精簡的數值特徵基準：method、Content-Type、一般 header 與 query/body 的長度、特殊字元、少量 SQL/XSS 詞法訊號，保留原文與一次 URL 解碼兩組特徵。沒有 TF-IDF、OpenAPI 契約或完整攻擊語意解析，不能當正式防護。平台、回應、session、路徑識別碼與認證 header 實值不進模型；JSON/form body 的常見憑證欄位排除，非 JSON/form 的原始字串 body 也保留字元訊號（不是完整內容解析器）。只支援解析後的 query dict、JSON/form body；送入不同格式前應擴充特徵並增加 VERSION、重新訓練。

```sh
python -m unittest discover -s sentinel/model -p test_model.py
```

合成資料測試驗證分組、憑證欄位排除、訓練及模型搬移後推論，不代表真實偵測效果。Linux 可執行性已測；Windows 實機需另外驗證。

## 評估證據

詳細指標與正式驗收建議見 [EVALUATION.md](EVALUATION.md)。每次訓練會輸出 report.md、report.json、predictions.csv、split.csv，包含準確率、各類 Precision／Recall／F1、Macro-F1、混淆矩陣、誤報／漏報率、ROC-AUC、Average Precision、最多類別基準、群組區間狀態及可追溯紀錄。每次實驗請指定新的輸出目錄，避免覆蓋舊結果；若該目錄已存在，必須是空的。


## API 文件導向的 header 候選

```sh
python sentinel/model/generate_api_data.py --output header-plan-001
```

預設路徑由程式位置解析，相容 Windows／Linux。讀取現行 active-api-manifest 與修正後契約，先驗來源 SHA；以歷史正常請求保留 method、path、query、body，針對所有文件 header 建立存在／省略計畫，對非憑證 header 加入 SQLi／XSS 候選。每筆附契約與人工參數文件 SHA、基底樣本 ID、模板與配對 ID。沒有自行添加 API 文件未宣告的自訂 header。

現行結果見 [62 操作候選表](generated-header-plan-62/candidates.csv)、[逐 API-header 核對表](generated-header-plan-62/header-coverage.csv) 與 [覆蓋明細](generated-header-plan-62/coverage.json)。先前版本移至 history/，不再作為現行覆蓋清單。

正式採用 Bagisto 21、Shopware 20、Sylius 21，共 62 操作；Shopware GET /checkout/gateway 與 Sylius GET /api/v2/shop/products-by-slug/{slug} 已移除。62 操作均有歷史正常請求基底，涵蓋 194 組 API-header，405 種可選有／無組合。每個文件 enum／已知值逐一變化，其餘值固定，不作 enum 值的完整笛卡兒積。必填／條件認證各自省略也有候選，與攻擊意圖分開；實際認證 OR／AND 關係仍須遵循契約。

共 2,944 個計畫：405 組可選有無、300 組文件值、47 組必填／認證缺失、2192 組攻擊意圖。候選 normal 共 752，SQLi 與 XSS 各 1096；這是計畫數，不是獨立訓練樣本數，相同 payload 換 API 不算新家族。

缺少實際 header 值時以 `${LIVE:header-name}` 明列待綁定需求，不杜撰有效語言 ID／憑證。此次聚焦 header 變化，沒有重做全部 query/body 情境。

所有候選均 http_executed=false、training_approved=false；沒有發送 HTTP、沒有新建有效 session、沒有宣稱正常對照有效或攻擊成功。即使 --allow-candidates 也會拒絕這些採集計畫。需由本機平台採集器先注入當次憑證、解析動態 ID、送出請求、保留證據，再人工審核。

請求輸入已改為 v2：dataset/core.py 新採集保留所有擷取到的 header、全部 query/body 與 path_parameters，憑證遮蔽、追蹤 ID 正規化。舊白名單僅用於 v1 歷史對帳，不是新訓練的選欄規則。HTTP 客戶端新增最終送出層 header 觀測，包含 Cookie、User-Agent、Host、Content-Length 等自動標頭；保存時仍遮蔽敏感值。舊採集器也取消任意 30 筆正常流程上限，保留所有已驗證正常操作。

特徵版本為 3，共 140 維，處理完整 query、body、path 與一般 header 的字元／詞法訊號；不是只取 query 或 firstName。純文字與畸形 JSON 不再被默默丟棄。憑證只保留結構，Host／URL authority 不進詞法特徵；不支援同名重複 header、完整 multipart/二進位本文或檔案內容解析，不能宣稱完整 WAF 能力。字元特徵不是原文逐字學習，也不保證所有不同請求都有不同向量。舊模型不可沿用。

相同 template_id 會跨平台綁定，避免這批少量固定模板同時進入訓練與測試。正式採集須先配置不同集合的獨立模板與 session，不能直接將此規劃表拿來隨機切分。


## 以真實請求為訓練來源

```sh
python sentinel/model/real_requests.py sentinel/dataset/reference/normal-candidates.csv --output refreshed-requests
```

工具逐筆核對 HTTP 證據、原 SHA、request ID、輸入與回應狀態後，重新輸出完整請求候選與 parameter-coverage.csv；不發送新請求、不自動核准。Windows CRLF／Linux LF 差異只在重建換行後完整 SHA 等於原紀錄時接受，記錄重建方式與目前位元組 SHA，不更改預期 SHA。

本次結果在 [完整參數覆蓋表](real-request-reference-v2/parameter-coverage.csv) 與 [完整請求候選](real-request-reference-v2/candidates.csv)。195 筆為同一批歷史正常請求重新匯出，不是新增樣本；並非使用者上傳 260 筆的完整替代。歷史 HTTP 客戶端未保存自動 header 的部分不能憑空補回，新採集才會完整觀測。

覆蓋表分 header/query/path/body，列出文件規則、存在／省略筆數、不同觀測值數，連文件沒有列但實際出現的欄位也保留。存在不等於已測完 enum、邊界或業務效果。例如 Bagisto /products 的 order/page/type 仍缺實測，per_page 也未具完整值域覆蓋；不得宣稱已具有泛化能力。

正式訓練須使用完整請求 v2 的人工審核結果；可直接將 export_reviewed.py 匯出的 JSONL 傳給 train.py。改前處理後審核不得自動沿用。新舊訓練統一由 features.py 重算特徵，不使用匯出檔附帶的舊 numeric_features。

既有 collect.py 的攻擊執行流程仍主要限搜尋／地址姓名，不能用它宣稱全部參數攻擊情境已採集。本次修正輸入、完整流程保存與覆蓋查核；缺少的真實參數變化仍需在已啟動的三平台上重新採集。目前雲端沒有這三平台的容器、.runtime 設定或 PowerShell 7，尚未進行新的三平台採集，沒有訓練新版正式模型。

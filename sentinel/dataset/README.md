# XGBoost 資料集試產

## 最新：只擴充訓練 v5

[small-api-v5](small-api-v5/README.md)：train594、test150、Sylius validation150、challenge96，共990筆。新增48組三類配對144筆，所有新增資料只進train，故主比例改為594:150:150，不再宣稱60/20/20。三份保留CSV與原v4完全相同，原始輸入不正規化；新增案例先通過全目錄骨架與原文近似隔離。仍62API／620文件位置、offline、無新HTTP證據。見 [補強與限制](../analysis/train-augmentation-v5.md)。

## 歷史：骨架分組 v4

[small-api-v4](small-api-v4/README.md) 為目前離線版本，筆數450/150/150＋challenge96與特徵v5不變。先按全域骨架／近似原文合併，再整群分集合；Sylius外部驗證獨立，Medusa排除。所有620位置保留、原始輸入不正規化，骨架分析只作輔助 metadata。舊v3保留比較；其97.33%不能代表新切分效果。見 [實作與限制](../analysis/skeleton-split-v4.md)。

## 歷史：文件導向 v3

[small-api-v3](small-api-v3/README.md) 為新離線候選：450/150/150主實驗，加96筆未見語境challenge，共846筆。三類等量、四位置配平、62API／620文件位置保留；Sylius只作外部驗證，Medusa不納入。一般test共享已見家族但模板不重複，challenge保留未見編碼／語境；舊v2及下方歷史紀錄不覆寫。v5特徵2402維，原文不正規化。

2026-11-09 CSV 顯示更新：現行 small-api-v2 的 train/test/validation 已移除「實際送出」「可正式訓練」兩欄；完整紀錄 JSON、請求、標籤、集合與內部 HTTP 證據檢查不變。舊歷史檔保留原狀。

## 歷史：小規模 v2，比例與參數補全

[small-api-v2](small-api-v2/README.md) 為目前候選版本：train/test/validation=252/84/84，共 420 筆（60/20/20），各集合三類等量。train/test 使用 Bagisto＋Shopware，validation 僅 Sylius 結合 httpParamsDataset，Medusa 排除。比例是小規模配置，不是研究有效性的充分條件；平台隔離、同來源分組與避免洩漏仍須維持。

三份文件的 620 位置保持覆蓋。原 43 個物件依語義補結構，部分其實是旗標或整個合法空本文；正常識別值改用已對帳的歷史證據，train/test 使用不同歷史流程來源。82 個憑證位置安全遮蔽不是遺漏；仍有 6 個條件商品種子、1 個自訂欄位定義、2 個選填關聯 null 的實機接受方式待確認。無 `${LIVE:...}` 佔位不代表實例現在可用，所有候選未核准訓練。見 [完成與待辦紀錄](small-api-v2/完成紀錄.md)。下方 v1 紀錄保留對照。

## 2026-11-09：小規模三集合候選

目前新版本見 [small-api-v1](small-api-v1/README.md)：train 165、test 38（Bagisto＋Shopware）、validation 118（Sylius＋固定版本 httpParamsDataset），共 321 筆候選，完全排除 Medusa。CSV 各自包含 Header、Query、Path、Body，並有逐欄覆蓋表。三份文件共 620 個參數位置皆出現在候選中；397 個已填合成／文件列值、180 個仍待憑證／實例值綁定、43 個物件結構待補。不能把欄位存在當成業務有效或實測成功。

舊讀表器曾把 Body 的 `query` 欄位誤認為 URL Query，已改為依表頭分辨，三份 API 文件原文不變。Docker 引擎檢查未連線成功，因此此次沒有平台 HTTP 證據，沒有正式訓練；本版本全部 `training_approved=false`。既有 CSV／JSONL 不覆寫，新候選來源、分割、未解問題見該目錄 README 與 provenance.json。

## 完整請求輸入更新

2026-11-09 使用者確認：主專案改為 Documents/GitHub/MSDSS，只修改必要程式，不搬入 Downloads 的執行環境／資料。新採集使用 request_input_version=3，保留原始 ID、email、path、大小寫、空白、編碼及所有觀測 header；只遮蔽憑證。raw_query／raw_body 與解析欄位分開保存；舊 v1/v2 只用於歷史證據對帳。歷史未擷取的原文不能補造。header 依三份 API 文件共 12 種不同名稱各自建立特徵，但不是 header-only 研究。

既有 CSV／JSONL、舊情境數與 v2 匯出目錄保持原狀；新候選另存 small-api-v1，不重新核准舊資料。先前 260 筆與 Sylius 評估來源不明，不作目前統計或有效評估。新格式、278 維特徵及重採要求見模型 README。下方 65 種輸入與舊正規化敘述是當時版本結果，不代表 v3。

完整參數覆蓋及舊資料重新匯出見 [模型說明](../model/README.md)。下方試產筆數與選定搜尋／地址欄位的敘述為原試產設計，不代表目前已覆蓋所有 API 參數。擴大輸入欄位不等於補齊訓練資料或完成泛化驗證。


更新日期：2026-11-08。使用者已同意執行資料集計畫。本目錄是新增的採集與審核工具，不改動原 API 文件、採用旗標、既有 Medusa／Mirage、根目錄 compose 或資料庫。

## CSV 閱讀版

已依使用者要求新增 UTF-8 BOM CSV，方便以 Excel 開啟，原 JSON／JSONL 保留：

- [正常請求表](reference/normal-candidates.csv)：195 列，每列一筆既有正常候選請求；含平台、方法、路徑、query、body、狀態、來源與審核資訊。
- [正常請求參數明細](reference/normal-parameters.csv)：944 列，將每筆請求的參數拆成位置、名稱與值，較容易閱讀；**一個請求會有多列，944 列不是 944 筆訓練樣本**。用請求序號或樣本 ID 對回正常請求表。
- [預定情境表](scenario-catalog.csv)：660 列尚未實際送出的正常／SQLi／XSS 候選模板；不是 660 筆實測資料。

CSV 只改儲存／閱讀格式，不改標籤、切分、去重或訓練流程。巢狀物件與字串以 JSON 儲存在儲存格，保留引號、換行、空值與型別；完整紀錄 JSON 欄供無損還原。轉換後已讀回逐筆比對全部正常請求與情境內容相同，原始檔 SHA 未變，憑證掃描通過，見 [轉換核對](reports/csv-conversion.json)。

只要讀入後的資料、特徵與切分一致，CSV／JSON 格式本身不影響 XGBoost 結果。Excel 手動改值、自動轉型或把參數明細每列誤當一筆樣本，會改變資料；目前訓練工具仍使用經審核的原始結構，沒有因匯出 CSV 而開始訓練。重新轉換可執行 to_csv.py，已有 CSV 時拒絕覆寫人工修改。

先前「65 種不同輸入」是現行程式的指紋計數；已發現 Shopware 查訂單的 filter.value 內訂單 ID 尚未統一，不能當成 65 種獨立情境。這次格式轉換保留原值，沒有順便修改這個待修正的去重問題。

## 目前狀態

已從七份既有、真實本機平台完整 passed 證據整理出 **195 筆 normal 候選參考資料**（Bagisto 56／Shopware 81／Sylius 58），涵蓋現行 62 操作。去除憑證及動態識別值後只有 **65 種完全不同的請求輸入**；不能把 195 筆當成 195 種獨立情境。它們保留原 request ID、來源證據與 SHA，並明列 `origin=historical_reference`，不是本次新採集。

本次新實機試產 **0 筆**、實測攻擊資料 **0 筆**、人工核准訓練資料 **0 筆**。首次檢查 C 槽約 1.97 GiB，21:02 再檢查為 2.67 GiB，Docker 引擎仍未開啟，既有啟動門檻至少 4 GiB；採集器已在磁碟檢查停止，未發送請求。最新量測見 [資源紀錄](reports/resource-status.json)。使用者會自行釋出空間後通知。程式的單元測試不是平台測試；完整採集器仍需實機驗證。

結果見 [執行紀錄](執行紀錄.md)、[既有正常資料摘要](reference/summary.json)、[去重／分組結果](reference/quality-v2.json)。所有候選仍待人工審核，沒有模型訓練或 TF-IDF 擬合。初次匯入的未補版本欄位資料另留 normal-candidates-initial.jsonl，對應 quality.json；目前以含固定版本的 normal-candidates.jsonl 與 quality-v2.json 為準。

## 試產設計

每平台規劃 30 筆正常購物流程、120 筆目標 normal（含 10 筆空白必填姓名的非攻擊錯誤）、50 SQLi、50 XSS，共約 250；三平台約 750 候選。30 筆流程不足時不複製補數。其餘前置／驗證讀回請求只存 HTTP 證據，避免為達筆數把輔助請求全算進去。

候選目標為商品搜尋及新增地址 firstName。地址模板來自當次正常流程的有效請求，登入／商品／國家等狀態由真正回應建立，不回放舊 Token 或固定 ID。每批以新的測試會員完成正常購物並查單，再重新登入確認身分。

搜尋在每批先測真實商品關鍵字與不存在的正常關鍵字，必須分別找到相同商品與得到空集合。無法證明過濾效果時，該批不用這個搜尋參數製作攻擊，改用已驗證的地址欄位並記錄原因。一般 normal 地址須重新查回同一 ID 與姓名；正常錯誤先有有效地址對照，再確認空白必填值受到 400／422 驗證拒絕。

攻擊候選和同位置 normal 以 pair_group 對應；50 個 SQLi／XSS 各只有**一個家族／平台**，共六個家族，分平台不共用家族。只是測試工具與品質閘門的少量試產，不足以代表廣泛未知攻擊。數字、大小寫等小變化不算新家族。正式擴充前須增加獨立家族與業務欄位，並檢查家族／平台混淆，不能憑這批試產宣稱跨平台泛化。

SQL 候選只含常數或 NULL 的辨識探查，沒有資料讀取、破壞命令或延遲；XSS 候選只使用 void 表達式，沒有外部連線、Cookie 讀取或資料外送。沒有管理端或真實付款。情境來源、候選標籤與家族都放 metadata，不放進實際請求的標頭或標記值。只對獨立本機平台送出，目標請求間隔至少 0.25 秒、單線執行。

## 資料界線與審核

- `input` 只包含 method、路由模板、query、安全必要 headers、遮蔽後 body。Authorization／Cookie／金鑰／密碼實值不進資料；動態資源 ID 與測試 email 正規化。
- `annotation` 保存 proposed_label、標籤依據、eligible_for_review、pending_human_review；**不自動宣稱已經人工審核**。
- `metadata` 保存平台、固定來源紀錄、映像 ID、來源／程式／契約 SHA、request ID、session、pair、家族、HTTP status 與業務斷言。這些不是推論特徵。
- 完整 response 僅保留於遮蔽 HTTP 證據，不輸入模型。沒有 HTTP 的候選模板不列成實測資料。401／403／429、連續 5xx 或正常對照失敗會停止；5xx 與前置拒絕不直接當有效攻擊樣本。
- `quality.py` 輸出完整／近似形式重複、候選標籤衝突、連通群組及平台留一外層候選。近似形式僅處理大小寫、空白與數字變化，語意近似仍須人工家族審核。大群組不拆散湊比例；內層 validation 尚未建立。
- `export_reviewed.py` 只接受明確 approve、final_label、reviewer、reason，並核對候選 SHA；缺證據或不具審核資格者不能強行核准。輸出也不代表已訓練模型；所有訓練讀取都只能使用 input，label 為答案，audit 分開。

## 操作順序

從 `C:/Users/USER/Downloads/MSDSS` 使用 PowerShell 7。工具不下載新映像或重灌資料。

```powershell
# 不連平台：候選模板與既有正常參考資料
python sentinel/dataset/scenarios.py
python sentinel/dataset/bootstrap.py
python -m unittest discover -s sentinel/dataset -p test_dataset.py
python sentinel/dataset/audit.py

# 先確認 Docker 引擎、至少 4 GiB 磁碟及既有記憶體檢查都通過，再逐個執行
./sentinel/dataset/run-pilot.ps1 -Platform bagisto
./sentinel/dataset/run-pilot.ps1 -Platform shopware
./sentinel/dataset/run-pilot.ps1 -Platform sylius
```

Wrapper 只啟動本次獨立 project；結束時只停止本次新增啟動的容器並保留資料卷，原本已在執行的容器保留。採集器另外檢查容器 project、127.0.0.1 綁定、固定埠號、單平台執行與剩餘磁碟。

每次另存 `pilot/平台-UUID.jsonl`、`evidence/平台-UUID-session-N.json`、`reports/平台-UUID.json`。重新執行建立新批次，不覆寫舊證據；每批需要五個真實訂單，先注意測試庫存，缺貨時停止，不能改既有資料庫或直接偽造庫存。

```powershell
# 將路徑換成實際 pilot 檔名；output 必須是新的檔名，避免覆蓋人工審核表
python sentinel/dataset/quality.py --input sentinel/dataset/pilot/實際檔名.jsonl --output sentinel/dataset/reports/實際檔名-quality.json
# 人工查看來源與請求，填寫產生的 .review.csv 後才執行
python sentinel/dataset/export_reviewed.py --input sentinel/dataset/pilot/實際檔名.jsonl --review sentinel/dataset/reports/實際檔名-quality.review.csv --output sentinel/dataset/reviewed/實際檔名.jsonl
```

審核完成與資料品質通過後，才實作／擬合 A、B、C 的 TF-IDF 與契約特徵、內層分組切分及 XGBoost。現在只有不需擬合的基本數值特徵函式，不宣稱三種模型方法已完成。所有擬合只用該回合訓練資料。Medusa 不出現在採集器平台選項，不參與詞彙表、特徵、門檻或模型選擇。

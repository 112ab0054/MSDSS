# MSDSS 目前專案狀態

更新日期：2026-11-09。此檔是工作摘要，不是 App 全域記憶或完整聊天匯出。

- 唯一主專案：C:/Users/USER/Documents/GitHub/MSDSS。只在此處修改必要程式／說明，不整批搬入 Downloads 的資料、執行環境或舊產物；Downloads 保留作來源參考。
- 2026-11-09 使用者確認：header 不作唯一主題，依三份人工 API 文件涵蓋已宣告 header，同時保留 query/body/path。新 request_input_version=3 保留原始 ID、email、path、header 值、大小寫、空白、編碼；只遮蔽憑證，不進行 ID／字串正規化。features VERSION=4，header 名稱從三份文件讀取並隨模型保存。
- 「260 筆」與先前 Sylius 分數來源不明，不當作目前資料數或有效評估證據。舊資料與 v1/v2 僅保留追溯，不自動沿用審核或模型。
- 三平台候選範圍共 62 操作：Bagisto 21、Shopware 20、Sylius 21；第一版 normal、sqli、xss。
- 最新候選 sentinel/dataset/small-api-v2：train 252／test 84 為 Bagisto＋Shopware，validation 84 為 Sylius 結合 httpParamsDataset 原始 payload；共 420、比例 60/20/20、各集合三類等量，Medusa 完全排除。這不是平台相似度排名。620 位置皆列入；物件依原始 schema 與核心程式補結構，正常識別值追溯不同歷史 session，82 個憑證位置維持遮蔽。6 個條件商品種子、1 個自訂欄位、2 個 null 關聯待實機確認。Docker Desktop 已嘗試啟動但 API 無回應，未新送平台請求，全部未核准訓練。v1 保留對照。
- Medusa 程式固定 2.22.4，bundled Store 規格 info.version=2.22.3，共 79 操作。Medusa 是凍結模型後的外部測試與 Demo。
- 現行範圍見 selected-apis.md 與 api-extension/active-api-manifest.json。16 份修正版另存 contract-corrections；讀取時依清單選用。
- 三份 API_parameters.md 已經人工修訂，包含 Shopware 原第 16、18、20、21 節（移除 gateway 並重編號後為第 15、17、19、20 節）的局部補正；不得使用歷史產生器整份覆寫。API 標題、用途、參數、說明與可輸入值的後續變更，只處理使用者指定範圍並比對差異。
- 序列化方式與拆開傳送不顯示於三份參數文件，原始 OpenAPI 的 style／explode 欄位仍保留。
- 舊 45 操作審查及舊保留／驗證報告已歸檔；當時的雜湊與通過結果不代表目前人工修訂版。看 history/README.md。
- 三平台已有正常主流程證據與 195 筆可追溯正常請求；GitHub 主目錄尚未重跑 v3 原文採集。歷史證據缺原始 target／body 時不補造，正式三分類資料與效果驗證尚未完成。單元測試的暫存合成模型不是正式訓練成果。
- 沙盒與 Mirage 由隊友負責，本次文件清理未修改其程式、部署或資料庫。

本次清理保留三份 API 參數文件、舊 Medusa 77 參數文件、原始規格及契約 JSON 的內容；更新現行索引與說明，舊產物移至歷史區。

2026-11-09 訓練資格更新：使用者要求移除人工審核及程式判斷。model/data_io.py 不再要求 training_approved 或 audit 的人工核准欄位；preflight 不再輸出人工審核相關欄位。真實 HTTP、v3 原文、session、來源證據及分割檢查仍保留；舊資料與審核紀錄不改寫。新版 Colab ZIP 另存 model/colab_upload_no_manual_review.zip。

2026-11-09 Colab 訓練修正：新增明確 --mode offline，允許現有生成請求做離線分類實驗，缺 HTTP／session 不再阻擋此模式；不改原資料狀態。--mode live 保留實機證據對帳。使用者已將 Notebook／套件改名為 model/msdss訓練.ipynb、model/dataset.zip，沿用此名稱；不復原舊名稱。

2026-11-09 最新：依XSS診斷新增small-api-v3，主資料450/150/150＋challenge96，共846；train/test共享已見家族但模板與操作隔離，challenge保留未見語境，Sylius外部原文重新抽樣排除v2曾用值。62API／620欄位置都保留，原API文件不改。特徵v5=2402維，原字元2–5gram固定hash及JS／編碼統計，無正規化／詞彙fit。舊v2、v4基準與dataset.zip已保留history/xss-v4-baseline。新版Notebook與dataset.zip沿用現名。Windows固定依賴打包訓練／搬移自測通過，Colab／Ubuntu需當地驗證；未新增HTTP證據。

2026-11-09 骨架分組更新：目前 small-api-v4／document-v4-skeleton-disjoint；先將所有本地／外部原文建立骨架與近似關聯，再整群分配。保留v3資料與Notebook/ZIP基準。846筆、62API、620文件位置、特徵v5/2402維與固定模型參數不變。原文不正規化，分組視圖不進特徵；重算目錄及實際樣本攔截跨集合近似變體。獨立相依群仍各1，不能報信賴區間。詳見 skeleton-split-v4.md；未新增HTTP證據。

2026-11-09 Colab骨架重算修正：Python3.11與3.13標準庫HTMLParser對一筆未封閉註解／CDATA外部XSS解析不同，已凍結CPython3.11.3解析器及markupbase並保留PSF授權、核對ID／SHA。107筆目錄／846筆樣本在3.11.3和3.13.13重算一致。CSV原文／骨架ID／分割不變，洩漏檢查保留；更新dataset.zip後需Colab第一格重新上傳解壓。

2026-11-09 v4誤判診斷完成：固定train-only模型重現396筆預測，機率誤差0。110筆重點錯誤（SQLi→normal47、SQLi→XSS39、normal→XSS24）。訓練SQLi150筆皆有註解訊號；無此訊號的86筆保留SQLi全錯，在副本追加--後85筆轉SQLi。normal誤報24筆對path.length高度敏感；純數值探針設17後24筆轉normal，非資料正規化或模型改善評估。已排除單靠中文說明文字的解釋。資料／文件／模型入口／ZIP未改，見v4-error-diagnosis.md及model/diagnosis-v4-2026-11-09。

2026-11-09 訓練補強v5完成：目前small-api-v5，共990筆（train594／test150／Sylius validation150／challenge96）。只追加48組三類配對144筆，24種無註解SQL與24種XSS原文，原450筆train保留；所有保留CSV bytes不變，preflight核對凍結SHA。原文／API文件／特徵與固定模型參數不改。一次探索性比較Accuracy84%／84%／73.96%，challenge SQLi Recall仍25%；未再依分數調整。新ZIP與Notebook沿用現名，舊v4包保存在history/train-v4-baseline，詳見train-augmentation-v5.md。未新增HTTP證據。

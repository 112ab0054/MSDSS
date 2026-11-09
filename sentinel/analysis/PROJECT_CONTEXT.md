# MSDSS 目前專案狀態

後續補證：密碼重設HTTP已確認產生新Token並使舊Token失效；搜尋可用GET /store/products?q=...；付款可透過建立API替換session（ID會改變）。原79操作分類仍為60／1／7／11，累計357筆HTTP與實際分數匹配、193項業務斷言通過。 [補證與替代API](Medusa剩餘項目再補證與替代API.md)。下列先前累計數字屬歷史輪次。

最新補資料實測：60成功、1部分成功、7前置不足、11版本／功能差異，not_run=0；339筆HTTP與實際gateway分數匹配，184項業務斷言通過。促銷、四種目錄明細、密碼更新、退貨及通用驗證碼已補通；通知／郵件送達仍未驗證。 [本輪實測紀錄](Medusa補測資料建立與驗收.md)。下列先前數字保留作歷史紀錄。

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

2026-11-09 Medusa正常查詢誤報診斷：已重現SQLi56.7988%，HTTPX預設Accept:*/*被聚合SQL註解正則視為/*。保持q=cotton與其他headers不變，Accept:*/*為SQLi53.7731%，application/json為SQLi6.7971%／normal68.4350%；application/*再誤報。模型／資料／規則未改，仍只告警。Medusa產品搜尋實際參數q與limit/offset，原query/page接線探針不等於正確業務請求；差異另記medusa-normal-false-positive-2026-11-09.md，未覆寫原文件。

2026-11-09 Accept修正完成：small-api-v6共1098筆（train702／150／150／96），只新增train108筆三類對稱傳輸header配對，所有保留CSV不變。特徵VERSION6仍2402維，只豁免Accept合法媒體型別位置萬用字元的SQL註解誤計，raw與hash保留；固定參數重訓，更新gateway完整model及Colab套件。正常query=cotton原SQLi56.8%轉normal88.84%，20個固定正常探針皆normal；整體Accuracy86%／86%／72.92%，challenge SQLi Recall21.88%未解。總白話紀錄為訓練版本與問題處理白話紀錄.md。舊v5套件存history/accept-v5-baseline。未新增真實Medusa業務證據、未改API文件／compose／Mirage。

2026-11-09 Git發布完整性修正：重現f1e6ed8直接Git匯出的44項模型測試6失敗，原因為Git text=auto eol=lf把CSV／凍結授權檔轉換換行，與原SHA不符。新增精確bytes保留屬性並恢復Git儲存格式，不改工作檔原內容、SHA檢查或模型。暫存索引候選Git樹重新匯出後46模型＋36資料＋16gateway=98全過，Git與ZIP preflight均ready且四份SHA相同；回歸測試涵蓋autocrlf true/false與真正換行篡改仍拒絕。驗證階段未建立commit或改主索引；後續依使用者要求提交推送。結果見git-artifact-integrity-verification.json及白話紀錄。

2026-11-09 攻擊面向顯示欄：新增small-api-v6-annotated，四份CSV在類別旁新增攻擊面向，多標籤用；分隔，normal不適用；外部圖片載入等標待確認，不改原3類標籤。1098筆原始儲存格及完整紀錄JSON逐筆相同，原v6全保留。來源與閱讀版CSV SHA分開存、凍結閱讀版，面向欄不被read_rows讀入、不進模型。預設訓練路徑及Colab包更新閱讀版，模型不重訓；111筆normal格式與外部標籤疑義未修。本輪未push。

2026-11-09 v7文件填值修正：仍1098筆，normal111語言ID改為歷史passed真值；723筆欄位修正／省略紀錄，844項已檢查問題降0，另修17筆壓縮criteria。請求內無MSDSS cotton；公司11種、部門6、搜尋term39/query24、郵遞區號7、生日3。592/620文件位置在normal出現，26選填未綁定／省略、2分支非實際欄位。攻擊原文／標籤／集合不變，從修正normal重嵌入並保存source ID映射，新輸入新SHA不冒稱舊保留題bytes相同。新preflight檢查文件正常值與規則指紋；舊通用fallback改為報錯。特徵6固定參數重訓gateway模型，Colab／inference-v7更新。實際Docker未啟動，歷史ID未重新驗證，HTTP仍0，未改API文件／compose／Mirage。完整狀態見白話紀錄。


2026-11-09 v8語言多樣性：修復Docker失效socket的啟動阻礙（runtime目錄改名保留，無資料清除），啟動既有獨立Shopware，GET language查得英文en-GB與德文de-DE，逐個GET context確認指定語言鏈。111筆normal分配英文54／德文57，同組攻擊同步背景語言，語言本身被注入時保留攻擊原文。145筆input改變，1098筆總數、三類標籤、集合、骨架不變，Sylius validation CSV bytes不變。新增small-api-v8、語言證據及新舊ID映射；Colab ZIP／Notebook／訓練預設改v8。gateway權重與inference-v7未改，須重訓後再替換；既有v7分數不能沿用。語言API成功不等於整批資料HTTP已送出。


## v9：不只改語言，還要按欄位意思填不同內容

本次只暫時啟動既有Bagisto／Sylius資料庫唯讀SELECT後停止，未部署應用或改資料庫設定。Bagisto只有en，Sylius有8語言、20國家，已據此修正離線資料；Sylius目前通路仍只分配en_US，沒有宣稱8語言HTTP驗收。國家／城市／郵遞區號／州省與巢狀地址成組產生，並擴充人名、公司、部門、電話、搜尋、備註等。所有至少出現3筆的語義自由文字欄位均至少3種值；只有1～2筆者與固定選項、憑證、實例ID另列原因，不湊數。

新版small-api-v9仍1098筆，原payload、標籤、骨架及集合不變；1036筆欄位修正、794筆input改變，包含保留集合，因此舊分數不能直接沿用。原v8與套件保留，Colab ZIP／Notebook／預設改v9，須重訓，gateway／inference-v7未改。完整計數、限制、來源及檢查見[參數語義與資料多樣性v9.md](參數語義與資料多樣性v9.md)。


## 使用者Colab v9模型與真實Medusa展示

使用者提供results_download (6).zip並授權取代模型、測Medusa與push。四份資料SHA與v9相同，完整manifest及三類跨環境自測通過；新模型e612214de592b01ec931cc73a100603928c89e747c61eebf3027424669f24993已取代gateway舊v7，舊套件另存歷史，沒有重訓、改權重或調門檻。

獨立gateway18085連既有真實Medusa9100，實際版本2.21.0，未修改Mirage／原網站路由／根compose。正常流程58筆、36項斷言成功，商品／註冊Bearer／地址／購物車增刪改／配送／原生離線付款／建單及讀回均成功，captured_amount=0。Cookie無法維持身分，locales與付款session更新404，另記限制。79項狀態42成功、6前置不足、2版本／功能差異、29未測，不宣稱全部完成。58筆正常意圖55normal、2XSS、1SQLi，誤判照實保存，只告警不封鎖。7筆額外唯讀搜尋探針含1筆SQLi漏判，也全部保留。詳細內容見[Medusa教授展示驗證v9.md](Medusa教授展示驗證v9.md)。


## Medusa剩餘API補測與runtime狀態同步

上次只記獨立表，沒有更新medusa-holdout-inventory.json的79個not_run，本次已逐項同步。79操作都有實際HTTP紀錄，含明確負向探查；47成功、2部分成功（促銷空陣列分支）、18前置不足、11版本／功能差異、1實測失敗（配送calculate500），not_run=0。合計172HTTP都有實際gateway分數，82項已執行斷言通過。

MFA400明確缺encryption key；Cookie200但沒有Set-Cookie，移除Bearer仍401；通知token無法取得所以不捏造確認；退貨訂單未履約400；空目錄用未發行ID做明確負向探查，不當正常成功。退貨原因明細200空物件也不列通過。兩個自己的顧客移轉申請與取消已用API、兩方訂單清單及唯讀DB的soft-delete記錄確認。沒有改既有服務／DB設定、Mirage或模型，不用Medusa重訓。最新MD、CSV、JSON及主manifest狀態一致，規格版本2.22.x與實際2.21.0分開保留。詳見[補測紀錄](Medusa剩餘API補測與runtime同步.md)。


## 依原API文件重新確認32項

找到Downloads原手寫77API文件，GitHub工作副本缺檔，新增逐位元原文快照，不改既有文件。原32項非成功操作逐一對照文件參數、原生2.21.0、安全設定、唯讀DB與實測。Cookie用正確真正HTTPS／憑證驗證／自動Secure Cookie已通，HTTP仍不通；移轉接受／拒絕以平台原生token及雙方清單／DB狀態驗證，通知未測。locales確定translation disable=true，非版本缺route；manual canCalculate=false且calculatePrice明確拋錯，所以500保留但分類為需支援計價provider。reset請求依文件送identifier回201，事件未獨立觀測，改部分成功，不把郵件當此API必填；update補email＋password仍需真正reset token。促銷及四種目錄資料庫0筆、退貨fulfilled_quantity=0已確認。

最新51成功、3部分成功、14前置不足、11版本／功能差異，not_run=0；251HTTP與分數匹配、129斷言通過。模型與訓練資料未改，也未改既有Medusa設定／DB結構／Mirage。具體32項與原文行數見[原文件復核](Medusa依原API文件逐項復核.md)。

# Medusa Gateway


最新Medusa狀態（依原文件復核後）：79項均有HTTP紀錄，not_run=0；51成功、3部分成功、14前置不足、11版本／功能差異。Cookie成功限真正HTTPS；移轉接受／拒絕使用原生token、通知送達未測。配送500保留，但已證實manual不支援動態計價，改列前置不足。[最新逐項補測](../analysis/Medusa剩餘API補測與runtime同步.md)。下文42成功／29未測屬第一輪歷史。

流程：網站 → gateway → XGBoost 分析副本 → 原始請求轉送 Medusa → 回傳後端結果。

主程式只有 [app.py](app.py)。所有請求照常轉送 Medusa，只有清單內的 [79 個操作](../analysis/api-extension/medusa-holdout-inventory.json) 送進模型偵測。
這份清單是偵測範圍，不是 API 存取白名單；其他 API 不會因此被 gateway 拒絕。
目前為觀察模式：模型判為 SQLi/XSS 也照常轉送，避免誤判直接封鎖 demo 操作。
目前已附使用者提供的Colab v9模型（特徵仍v6），預設直接載入，不需為啟動再次訓練。來源與推論流程見 [MODEL.md](MODEL.md)。

## 安裝與啟動

在專案根目錄執行，建議 Python 3.12：

```sh
python -m pip install -r sentinel/gateway/requirements.txt
```

Linux／macOS：

```sh
export MEDUSA_UPSTREAM=http://127.0.0.1:9000
python -m uvicorn app:app --app-dir sentinel/gateway --host 127.0.0.1 --port 8080 --no-access-log
```

Windows PowerShell：

```powershell
$env:MEDUSA_UPSTREAM='http://127.0.0.1:9000'
python -m uvicorn app:app --app-dir sentinel/gateway --host 127.0.0.1 --port 8080 --no-access-log
```

安裝 gateway 的 requirements 已包含 XGBoost 與特徵依賴。啟動預設載入程式旁的 `model/`，不受目前工作目錄影響。
若要換模型，設定 `GATEWAY_MODEL_DIR` 指向完整解壓後的 `inference` 目錄，不是 model.json 或 ZIP。
設定 `GATEWAY_MODEL_DIR` 為空字串可以明確停用偵測，只保留轉送。
使用同版特徵 v6、請求格式 v3 的完整套件；不要把單獨修改過的程式混入舊 manifest。
啟動會載入一次模型並執行套件自測，通過後顯示 `model_ready mode=offline exploratory=True`；失敗會顯示 `model_load_failed` 並僅轉送。
已附模型與專案推論程式逐檔相符，權重與manifest維持本次重訓輸出原樣，舊上傳套件保存在歷史目錄；Git 也針對該目錄保留原始 bytes，避免換行改變 SHA。
離線模型可做 demo 分析，預測日誌保留 `mode=offline`、`exploratory=True`；自測通過不代表準確率或平台實測通過。

## 79 個操作的偵測範圍

依「HTTP 方法＋路徑模板」判斷，從既有 `sentinel/analysis/api-extension/medusa-holdout-inventory.json` 讀取。
部署時保留清單的相對位置；缺檔或不符 79 個不重複操作時拒絕啟動，避免默默使用錯誤範圍。

| 請求例子 | 模型偵測 | 轉送 Medusa |
|---|---|---|
| `GET /store/products?page=2` | 是 | 是 |
| `GET /store/products/product_123` | 是，符合 `{id}` | 是 |
| `POST /store/products` | 否，方法不在選用操作內 | 是 |
| `GET /admin/users`、未知路徑 | 否 | 是 |
| `OPTIONS /store/products` | 否 | 是 |

query 不影響 API 身分；header、query、body 不額外限制欄位。
以原始路徑比對模板，轉送也保留原始 bytes；`{id}` 中的 `%2F` 或編碼攻擊仍進入偵測，不先解碼成多段而漏掉分析。
真正額外的路徑段或不在清單內的方法略過模型，仍交給 Medusa。
表中的「偵測：是」表示符合範圍；還需成功載入模型，忙碌或逾時時可能略過／未即時完成，詳見下方說明。
後端的認證、路由與業務規則照常生效：若 Medusa 回 401/404 等狀態，就原樣回傳，不是 gateway 的清單限制。
本版沒有額外的健康檢查 API，模型是否載入可查看啟動日誌。

## 網站如何接入

保持 Medusa 在原本的埠，例如 9000，將 storefront 的後端位址指向 gateway：

```dotenv
MEDUSA_BACKEND_URL=http://127.0.0.1:8080
NEXT_PUBLIC_MEDUSA_BACKEND_URL=http://127.0.0.1:8080
```

```text
網站 → gateway → 選定 79 操作：模型偵測後轉送 → Medusa
               → 其他 API：略過偵測直接轉送 → Medusa
```

修改後重啟／重新建置 storefront，讓伺服器端與瀏覽器端呼叫都經過 gateway。
目前尚未替你修改 storefront 環境設定；請依實際部署填入位址。
瀏覽器須能存取該主機；Docker 內的 `127.0.0.1` 只指容器本身，須換成可連通的服務名稱。
CORS 預檢 OPTIONS 會轉送 Medusa，公開網域、CORS 與 Cookie Domain 仍須配合實際網站設定。

## 程式如何處理請求

- `model_request`：保存 method、原始 path/query、所有觀測 header 與本文。JSON/form 解析成副本，畸形 JSON 保留文字；共用訓練端規則遮蔽憑證。
- `analyze`：在執行緒中建立副本並推論，只記類別、三類機率、來源模式及探索性標記；錯誤只記類型，不記密碼、Cookie 或原始內容。
- `proxy`：只對選定操作呼叫模型，所有請求都用原始 bytes 轉送，保留重複 header；Host/Content-Length 由 HTTPX 重建，逐段連線 header 移除。
- 直接建立上游 Request，不合併共用 client 的 CookieJar，避免不同使用者串用登入 Cookie；後端的多個 Set-Cookie 原樣交回各自瀏覽器。
- 回應逐塊轉送原始 bytes，不先解壓 gzip；後端的 401/404/422/500、Location 等照實保留，不自動追蹤重新導向。上游逾時回 504，連線失敗回 502。

模型分析預設最多等 **0.2 秒**，可用 `GATEWAY_ANALYSIS_TIMEOUT` 設定有限正數秒數。
超時只停止等待，不會強制殺掉執行緒；同程序最多一個背景分析，尚未結束時的新請求略過分析並記警告，不堆進推論佇列。
這表示過載時部分請求沒有分類結果，不能把轉送筆數當成模型分析筆數。

## 測試與限制

```sh
python -m unittest discover -s sentinel/gateway -p 'test_*.py'
```

測試以模擬上游及假模型驗證：79 個操作會分析、其他路徑／方法只轉送不分析、編碼攻擊 ID 仍進入偵測、原文與憑證副本、Cookie 隔離、重複 Set-Cookie、gzip、302、4xx/5xx、推論失敗／超時、form、畸形 JSON、二進位標記與模型載入狀態。
另有本機 TCP 上游測試，確認真正 HTTPX 傳輸保留原始路徑／query、gzip 與 Cookie 隔離。
另有5項使用真實模型測試（含Accept誤報回歸）：原套件 SHA、預設載入與真實三類機率、中文／空白路徑搬移、損壞套件拒載。
共16項測試驗證接線與容錯；不等於 Medusa 的 79 個業務成功證據，也不是新增的模型準確率評估。

請求本文目前整段讀入記憶體，尚無大小限制；multipart／二進位檔案未做完整內容分析。
回應為 HTTP 串流，但尚未完成 SSE 的長連線驗證；不支援 WebSocket。
推論執行緒卡死時後續分析會持續略過，需重啟服務恢復，關閉程序也可能等候該執行緒。
尚未宣稱可直接用於正式環境。上面的啟動命令關閉一般 access log，避免 query 中的憑證進入網址日誌；預測結果仍會輸出。

模型只在啟動時載入，已在執行的gateway需重啟才會載入目前v9權重。原始API文件與保留評估資料未改；版本歷程、問題原因、修正及分數見[白話紀錄](../analysis/訓練版本與問題處理白話紀錄.md)。

歷史v7資料、特徵版本v6：模型按正常值修正後重訓，啟動後才載入；舊程序需重啟。模型來源見model-source.json；原API格式不合與尚未實機綁定的差異已記錄，不能沿用v6數據當當前效果。


## 本次教授展示

使用者Colab v9模型已取代專案舊權重；明確入口http://127.0.0.1:18085，連到真實Medusa2.21.0 http://127.0.0.1:9100。沒有把原Mirage網站切流。主要購物建單36項斷言通過，正常意圖58筆有3筆誤判，仍只告警。79項API狀態與版本／Cookie限制及重跑方式見[教授展示驗證](../analysis/Medusa教授展示驗證v9.md)。

gateway推論日誌新增request_id，僅允許UUID格式，其他內容記unavailable；不改請求／特徵或回傳資料，用於將實際線上分數與遮蔽HTTP證據比對。

最新[依原API文件逐項復核32項](../analysis/Medusa依原API文件逐項復核.md)，包含原文件快照、參數檢查、設定／資料庫／原生實作證據與HTTPS補測。未修改原API文件或模型。

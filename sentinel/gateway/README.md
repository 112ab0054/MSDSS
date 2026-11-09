# Medusa Gateway

2026-11-10：所有經過此gateway、支援的HTTP方法與路徑都送入模型分析，之後原樣轉送Medusa。原始77項清單只供API文件與驗證，已不限制模型偵測，也不再是啟動必需檔案。管理API、未知路徑、HEAD與OPTIONS都會分析；不支援WebSocket。

目前為觀察模式，判成SQLi或XSS也不封鎖。只有實際經過gateway的流量才能分析；直接連Medusa的請求不會自動被攔截。所有路徑均分析不代表模型已對所有API完成準確率驗證。

## 啟動

從專案根目錄執行，建議Python3.12：

```sh
python -m pip install -r sentinel/gateway/requirements.txt
```

PowerShell：

```powershell
$env:MEDUSA_UPSTREAM='http://127.0.0.1:9000'
python -m uvicorn app:app --app-dir sentinel/gateway --host 127.0.0.1 --port 8080 --no-access-log
```

Linux：

```sh
export MEDUSA_UPSTREAM=http://127.0.0.1:9000
python -m uvicorn app:app --app-dir sentinel/gateway --host 127.0.0.1 --port 8080 --no-access-log
```

MEDUSA_UPSTREAM為真正後端origin，不可填gateway自身。Docker內需使用服務名稱。模型預設是gateway/model完整套件；GATEWAY_MODEL_DIR可指定另一套完整套件，空字串明確停用模型。

網站的伺服器端與瀏覽器端後端位址都需指向gateway。實際認證、CORS與路由結果仍由Medusa決定；沒有修改現有storefront或Medusa設定。

## 分析與轉送

- 支援GET、POST、PUT、PATCH、DELETE、OPTIONS、HEAD，不以77項清單篩選。
- 模型輸入是遮蔽憑證的副本；後端收到原始方法、path、query、body與認證資料。沒有改特徵或重訓模型。
- 單模型序列推論。忙碌的請求等待，不再analysis_busy略過，因此併發或慢模型會增加延遲。
- GATEWAY_ANALYSIS_TIMEOUT預設0.2秒，現在是analysis_slow等待告警門檻；超過後仍等本筆分析完成，不取消或直接略過。不是回應時間上限。
- 客戶端中斷時，已開始的背景推論仍受shield保護；下一筆先等它完成，避免同時使用模型。
- 模型未載入／推論失敗時仍轉送，日誌如實記錄。Docker入口要求啟動時模型載入及自測成功。
- 每筆UUID對應預測日誌與轉送；只記類別、分數、模式、UUID及錯誤類型，不記整筆請求、密碼或Cookie。
- 原始bytes、重複query、Cookie隔離、Set-Cookie及壓縮回應的轉送規則保留。
- 二進位本文只保留既有格式的長度等特徵，不能宣稱已解析檔案內容。

## 模型與驗證

目前仍是使用者Colab v9模型，feature v6／input v3，offline、exploratory；模型SHA未變。完整model/與共享predict.py、features.py、request_input.py需同版，.gitattributes保留模型bytes。

```sh
python -m unittest discover -s sentinel/gateway -p 'test_*.py'
```

測試涵蓋原77、清單外路徑、各種方法、忙碌排隊、實際XGBoost載入與機率日誌、憑證遮蔽及原始HTTP轉送。模擬上游測試不冒充真實Medusa驗收。歷史實測與[本次還原說明](../analysis/Medusa驗證與展示.md)分開記錄。

部署見[DEPLOY.md](DEPLOY.md)。不要直接覆蓋隊友根compose、.env或私人金鑰。

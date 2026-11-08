# Medusa 閘道骨架／交接

此版只告警，不封鎖、不修改 API 文件、不使用回應推導攻擊標籤。尚未接入商城設定，尚未用 Medusa 完成端到端測試。

使用 Python 3.12，在虛擬環境安裝本目錄 requirements.txt；要呼叫模型，再安裝 ../model/requirements.txt。

```sh
python -m pip install -r sentinel/gateway/requirements.txt
python -m pip install -r sentinel/model/requirements.txt
```

Linux：
```sh
export MEDUSA_UPSTREAM=http://127.0.0.1:9000
export GATEWAY_MODEL_DIR=/你的模型資料夾
python -m uvicorn app:app --app-dir sentinel/gateway --host 127.0.0.1 --port 8080 --no-access-log
```

PowerShell：
```powershell
$env:MEDUSA_UPSTREAM='http://127.0.0.1:9000'
$env:GATEWAY_MODEL_DIR='C:\你的模型資料夾'
python -m uvicorn app:app --app-dir sentinel/gateway --host 127.0.0.1 --port 8080 --no-access-log
```

GATEWAY_MODEL_DIR 不設或載入失敗時僅轉送。必須使用與 features.py VERSION=3 相容的模型，勿沿用先前版本。沒有附已正式訓練完成的模型。預設不保存請求本文與憑證；關閉 access log 避免 query 中敏感資訊進入一般日誌。

## 下一個 Codex 接續事項

1. 啟動測試 Medusa，先測健康檢查、登入 Cookie、商品搜尋、購物車，確認原始本文、重複 query/header、Set-Cookie、gzip、重新導向正常轉送。
2. 接入正式審核後的模型；核對閘道輸入與訓練前處理一致。現在沒有依 API 契約提取 path_parameters，實際 path 直接進特徵，須補齊與訓練端的路由正規化。
3. multipart、檔案、二進位本文目前只產生不支援格式標記；不能宣稱已檢測內容。補完整解析、大小／深度限制、串流、WebSocket/SSE。
4. 模型放入獨立 worker，增加有界佇列、硬性逾時、過載時略過分析及指標。目前模型卡住仍可能拖慢請求，不是完整容錯閘道。
5. 驗證 Host 改寫、公開 URL、CORS、Cookie domain/path、代理信任設定；目前不偽造 Forwarded/X-Forwarded-*。
6. 增加測試與依賴鎖定；只記錄去識別化結果，模型錯誤不得把憑證印出。
7. 驗證未知路由也會分析並轉送，包括 404；不要求 79 個 API 都業務成功才擷取請求。

這只是可接續的開發骨架，未宣稱正式環境可用。使用者優先要求 Demo 正常操作，因此預設維持只告警。這批新增檔案尚未提交／推送。

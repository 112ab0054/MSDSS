# API 文件來源與採用範圍

更新日期：2026-11-08。本頁為目前來源、版本與採用狀態的總表。OpenAPI 是欄位與流程依據，不能代替已標記流量、實機驗證或模型效果。

## 三個訓練平台

| 平台 | 選定操作數 | 已保存的規格 | 規格 info.version | 部署／資料狀態 |
|---|---:|---|---|---|
| Bagisto | 21 | [Shop API](sentinel/analysis/api-contracts/bagisto/openapi-shop.json) | 2.4.10 | 尚未對應固定實例並跑通流程 |
| Shopware | 21 | [Store API](sentinel/analysis/api-contracts/shopware/storeapi.json) | 6.7.9999999-dev | 開發版快照，須換成與固定實例相符的版本 |
| Sylius | 23 | [Demo API](sentinel/analysis/api-contracts/sylius/openapi-demo.json) | 0.0.0 | Demo 文件，不能由此推定 framework 版本；須由固定實例重新匯出 |

三平台共 64 個候選操作，角色為 57 核心、6 流程支援、1 選用。Sylius 的顧客驗證請求路由因固定實例不存在，已從現行採用清單移除；原始規格仍保留作來源快照。第一版採 normal、sqli、xss。原始來源 commit、URL 與實際 SHA-256 見 [快照來源](sentinel/analysis/api-contracts/README.md)。目前 ready_for_collection 均為 false。

- [完整 API 索引](sentinel/analysis/selected-apis.md)
- [採用清單](sentinel/analysis/api-extension/active-api-manifest.json)：機器解析的來源與修正版路徑。
- [實施計畫](sentinel/analysis/api-extension/plan.md)：正常流程、前置狀態與驗證。

正式收集前，記錄固定版本／commit、API 套件、啟用模組、channel／locale、測試商品與付款設定；核對契約來源與雜湊，再以實際 request/response 跑通完整購物流程。不得把「已保存規格」寫成「已部署驗證」。

## Medusa 外部測試與 Demo

| 項目 | 目前依據 |
|---|---|
| 應用套件版本 | backend/package.json 固定 2.22.4 |
| Store／Admin 規格 | backend/static/openapi；info.version 保留上游 2.22.3 |
| Store 規格範圍 | 79 操作、69 路徑，包含 /auth 與 /store |
| 人工參數文件 | [Medusa_77_API_填寫參數.md](Medusa_77_API_填寫參數.md) 保留作舊版參考，不能當作現行完整清單 |
| 版本與舊部署描述 | [Medusa 文件狀態](MSDSS_部署核對紀錄.md) |
| 現行待測清單 | [79 操作索引](sentinel/analysis/api-extension/medusa-holdout-inventory.json)，非已通過結果 |

模型、特徵、詞彙表、類別順序、門檻及套件版本固定後，才測 Medusa；Medusa 不參與訓練或門檻選擇。若用 Medusa 調整，另列調適版並保留直接移植結果。

## 資料與維護規則

攻擊標籤來自審核過的情境，不由 HTTP status、規則或模型預測反推。憑證實值、密碼、Cookie、Authorization 與 API key 不進模型或一般資料集；response 僅供核對，不作推論特徵。

API 參數文件保留現有格式；後續只對明確指定問題做局部修訂並比較差異。不要執行歷史重建工具覆蓋目前人工修訂內容。歷史快照的通過結果不自動適用於現在的文件，見 [歷史紀錄](sentinel/analysis/history/README.md)。

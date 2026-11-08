# 三平台 API 增補採用計畫

目前採用 62 個操作。三份 API_parameters.md 已有後續人工局部修訂，以現存參數文件為準；本計畫與 active-api-manifest.json 記錄採用範圍及流程，不用歷史產生器覆寫參數文件。

## 採用範圍

62 個操作：Bagisto 21、Shopware 20、Sylius 21。56 個核心、6 個流程支援；每平台操作數不必相同。

Shopware GET /checkout/gateway、Sylius GET /api/v2/shop/products-by-slug/{slug} 不納入現行 62 操作；Sylius 顧客驗證請求也維持排除。來源規格保留供追溯。

第一版標籤固定為 normal、sqli、xss。歷史五分類規劃中的 CMDi 與 path_traversal 需有既有功能的合理輸入情境及人工審核，再另立實驗。

`[]` 表示陣列元素，分支標記表示不同可接受結構，不是實際欄位名稱。列舉值逐項保留；範例不是全部選項，自由文字與實例 ID 無法列成有限字串清單。巢狀必填只在父物件或該分支成立時適用，唯讀欄位不應送入。

## bagisto 新增 6 個操作

| 角色 | Method | Path | 用途 |
|---|---|---|---|
| 核心 | POST | `/customers` | 建立顧客帳號，供登入與會員購物流程使用 |
| 核心 | POST | `/customer-addresses` | 新增顧客地址，供後續查詢與更新使用 |
| 核心 | POST | `/checkout-shipping-methods` | 保存目前購物車選用的配送方式 |
| 核心 | GET | `/payment-methods` | 取得目前購物車可使用的付款方式 |
| 核心 | POST | `/checkout-payment-methods` | 保存目前購物車選用的付款方式 |
| 流程支援 | POST | `/cart-tokens` | 建立或取得訪客購物車的識別憑證，供後續購物車與結帳流程使用 |

### 基底網址與正常流程

來源 servers：`[{"url": "{url}/api/shop", "description": "Bagisto Shop API", "variables": {"url": {"default": "http://localhost:8000", "description": "Base URL of your Bagisto installation."}}}]`。

1. 確認基底為 /api/shop；設定實例要求的 X-STOREFRONT-KEY，核對來源繼承 bearer 與實際公開端點的差異。
2. 訪客呼叫 POST /cart-tokens 取得並延續 sessionToken；會員則 POST /customers 建帳、POST /customer/login 登入。帳號與訪客狀態分開。
3. GET /products 取得商品識別值；POST /add-product-in-cart 加入商品；POST /cart 讀取／重新計算目前購物車，並非每次新建。
4. 以 POST /update-cart-item 和 POST /remove-cart-item 測試數量與移除；需要時重新加入商品。
5. POST /customer-addresses 建立會員地址後才更新／查詢；POST /checkout-addresses 保存結帳地址。
6. GET /checkout-shipping-methods 取得可用方式，再 POST /checkout-shipping-methods 保存。
7. GET /payment-methods 取得可用付款，再 POST /checkout-payment-methods 保存；只用測試付款方式。
8. POST /checkout-orders 建單；redirect=true 只是進入付款跳轉，不能當成已建單成功；完成測試付款後核對 GET /customer-orders。

### 正式收集前

- 尚未記錄固定部署版本、模組設定、測試帳號與商品種子，也未逐一跑通正常購物流程。
- 需確認認證、session／context 延續與契約宣告一致，並保存實際 request/response 對帳結果。
- 目前規格 info.version=2.4.10 尚未對應已部署實例；上游少數 properties=[] 需以實例與版本文件核對，不自行編造欄位。

## shopware 新增 6 個操作

| 角色 | Method | Path | 用途 |
|---|---|---|---|
| 核心 | PATCH | `/checkout/cart/line-item` | 更新購物車品項，例如修改數量 |
| 核心 | PATCH | `/context` | 更新目前情境的地址、配送、付款與語言等設定 |
| 核心 | POST | `/order` | 查詢顧客訂單列表；不是建立訂單 |
| 流程支援 | GET | `/context` | 讀取目前購物情境並核對其設定 |
| 流程支援 | GET | `/payment-method` | 查詢可供設定的付款方式 |
| 流程支援 | GET | `/shipping-method` | 查詢可供設定的配送方式 |

### 基底網址與正常流程

來源 servers：`[{"url": "/store-api"}]`。

1. 基底為 /store-api；配置 sw-access-key，GET /context 或 GET /checkout/cart 取得情境，後續沿用 sw-context-token。
2. 以 POST /account/register 建帳（確認實例的信箱驗證設定），POST /account/login 登入；回應若更新情境 token，後續換用新值。
3. 查詢商品，再 POST /checkout/cart/line-item 加入；PATCH 同一路徑改數量，POST /checkout/cart/line-item/delete 移除。
4. POST /account/address 建立地址；GET /payment-method、GET /shipping-method 查詢可選值。
5. PATCH /context 保存地址、配送與付款；GET /context 核對。GET /checkout/gateway 不在現行採集範圍。
6. POST /checkout/order 建立測試訂單；POST /order 查詢結果，不混淆兩者。

### 正式收集前

- 尚未記錄固定部署版本、模組設定、測試帳號與商品種子，也未逐一跑通正常購物流程。
- 需確認認證、session／context 延續與契約宣告一致，並保存實際 request/response 對帳結果。
- 目前來源是 6.7.9999999-dev，須更換為與固定實例相符的契約，重新核對差異與 SHA。

## sylius 新增 8 個操作

| 角色 | Method | Path | 用途 |
|---|---|---|---|
| 核心 | POST | `/api/v2/shop/orders` | 建立購物車／訂單並取得 tokenValue |
| 核心 | PUT | `/api/v2/shop/orders/{tokenValue}` | 設定購物車的 email、帳單地址、配送地址或優惠碼 |
| 核心 | PATCH | `/api/v2/shop/orders/{tokenValue}/items/{orderItemId}` | 更新指定購物車品項的數量 |
| 核心 | DELETE | `/api/v2/shop/orders/{tokenValue}/items/{orderItemId}` | 移除指定購物車品項 |
| 核心 | PATCH | `/api/v2/shop/orders/{tokenValue}/shipments/{shipmentId}` | 設定該配送紀錄選用的配送方式 |
| 核心 | PATCH | `/api/v2/shop/orders/{tokenValue}/payments/{paymentId}` | 設定該付款紀錄選用的付款方式 |
| 流程支援 | GET | `/api/v2/shop/orders/{tokenValue}/shipments/{shipmentId}/methods` | 查詢該配送紀錄可選的配送方式 |
| 流程支援 | GET | `/api/v2/shop/orders/{tokenValue}/payments/{paymentId}/methods` | 查詢該付款紀錄可選的付款方式 |

### 基底網址與正常流程

來源 servers：`[{"url": "/", "description": ""}]`。

1. 先核對部署的 channel、locale、帳號與訪客權限、JSON-LD IRI 格式；目前來源 root 宣告 JWT，不代表已完成訪客權限測試。
2. 以 POST /api/v2/shop/customers 註冊、POST /api/v2/shop/customers/token 登入；郵件驗證請求屬選用。
3. POST /api/v2/shop/orders 建購物車，保存回應 tokenValue；查詢商品後加入 items，沿用此 token。
4. PATCH /api/v2/shop/orders/{tokenValue}/items/{orderItemId} 更新數量；DELETE 同一路徑移除品項。
5. PUT /api/v2/shop/orders/{tokenValue} 設定 email 與地址；顧客地址 CRUD 與訂單地址分別依契約填寫。
6. GET /api/v2/shop/orders/{tokenValue} 取得 shipmentId、paymentId；使用各自 /methods 查詢可選值，再 PATCH 對應 shipments/payments。值依契約可能是 IRI，不硬填裸 ID。
7. PATCH /api/v2/shop/orders/{tokenValue}/complete 完成測試結帳；PATCH 依契約使用 application/merge-patch+json，不能一律用 application/json。

### 正式收集前

- 尚未記錄固定部署版本、模組設定、測試帳號與商品種子，也未逐一跑通正常購物流程。
- 需確認認證、session／context 延續與契約宣告一致，並保存實際 request/response 對帳結果。
- Demo 規格版本為 0.0.0；來源 README 已記錄公開 Demo URL，但擷取時間與固定實例版本未核對，正式收集前須由固定實例重新匯出。

## 訓練、驗證與 Medusa Demo

三平台各自先跑通正常購物、合法特殊字元與非攻擊錯誤，再製作合理位置且經人工審核的 SQLi／XSS 嘗試。支援端點的正常請求也需檢查誤報；不要求每個 API 都有每種攻擊。按共同業務事件控制平台與類別分布。

先依 session／操作批次、模板家族及近似請求分組。共用模板家族不能跨訓練與外層測試；前處理、詞彙表只 fit 訓練資料。平台名稱、標籤、情境名稱與回應結果不作推論特徵。密碼、憑證與金鑰實值不進一般資料集或模型。

三回合平台留一：Bagisto＋Shopware→Sylius；Bagisto＋Sylius→Shopware；Shopware＋Sylius→Bagisto。保留平台是外層測試，只用訓練平台內的分組 validation 做提前停止、選方法與門檻。最後以三平台重訓並凍結模型、特徵、詞彙表、類別順序、門檻與版本，再測 Medusa。

報告各平台／業務事件的樣本數、正常誤報率、各攻擊 precision／recall／F1、Macro-F1、混淆矩陣與新增延遲（含 p95）；未測端點明列未測。這些結果不支持『所有電商平台一定有效』。

Medusa 為外部測試與 Demo，不加入訓練或門檻選擇；用 Medusa 調整時另列調適版並保留直接移植結果。套件固定 2.22.4、bundled Store 規格 info.version=2.22.3，目前包含 79 操作／69 paths。原 77 文件不改，現行待測操作另存 medusa-holdout-inventory.json，所有實測狀態起始為 not_run。

Demo 使用隔離測試帳號、商品與測試付款，先重跑固定正常流程；測試端獨立保存 request_id、替代 session ID、預期／實際結果與伺服器紀錄對帳。Medusa 部分前置拒絕不進目前 logger，不能把沒有日誌當成已防禦。此計畫未改部署、資料庫、沙盒或 Mirage。

## 目前完成與未完成

已完成過契約存在性、來源 SHA、認證結構與參照的離線核對。參數文件後續已有人工修訂，舊保留／驗證報告只代表當時快照，不作為現況完整性證明；每次局部修改仍須核對差異。未完成：固定三平台實例、端到端正常流程、正式訓練資料、模型訓練與效果驗證。ready_for_collection 保持 false。

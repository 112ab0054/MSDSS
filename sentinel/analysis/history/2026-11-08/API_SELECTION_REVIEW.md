# MSDSS 三平台訓練 API 選擇審查

日期：2026-11-08（Asia/Taipei）。工作目錄：`C:/Users/USER/Downloads/MSDSS`。

## 結論

商品、認證、地址、購物車與訂單的核心方向合理，不需整批推翻。但目前是 **45 個候選操作**，不是可直接產生完整購物資料的已驗證清單。正式收集前需修復拆分契約、補足流程依賴、固定實例版本及釐清分類範圍。

本次只讀程式與契約，沒有登入或操作三平台實例，沒有生成攻擊流量、建立訂單、修改資料庫、模型、沙盒或 Mirage。只新增此審查報告及專案上下文摘要；原 45 個選用檔與文件未改。

## 掃描結果

- `sentinel/` 只有研究計畫與契約，目前沒有訓練資料、訓練程式或模型，與其 README 相符。
- 三平台各 15 個操作，全部能在本機保存的原始 OpenAPI 找到相同 method/path，45/45 通過靜態存在性檢查。
- 去除 example/examples 差異後，有 16 份拆分操作仍與原始契約不同：Bagisto 登入 1 份，以及 Shopware 全部 15 份。這不是單純遮罩範例。
- 新後端依賴為 Medusa 2.22.4。`backend/static/openapi/store.yaml` 的 info.version=2.22.3，共 79 個操作、69 個路徑；比舊 77 個多 `POST /store/search` 與 `POST /store/payment-collections/{id}/payment-sessions/{session_id}`。

## 必須先處理的問題

### P1：遮罩流程破壞契約結構

- `selected-api-contracts/bagisto/post-customer-login.json` 的 `operation.requestBody.content.application/json.schema.properties.password` 應是 schema 物件，卻變成 `<redacted>` 字串。結果會讓解析器不再知道密碼欄位的型別、約束與描述。
- Shopware 15 份檔案的 security requirement 中，`ApiKey: []` 或 `ContextToken: []` 被改成 `<redacted>` 字串。OpenAPI 的 scopes 必須是陣列；這些是方案名稱與結構，不是憑證值。
- 修正方向：由未改的原始快照重新抽出；只在 example 或實際請求／回應資料中遮罩敏感值。不可對契約 properties/security 的鍵名做整節替換。
- 同步重產 API_parameters.md。Shopware 的參數表漏列 securitySchemes 定義的 `sw-access-key` 與需要的 `sw-context-token`；它們不是可省略的普通可選參數。

### P1：Sylius 缺少購物車建立與結帳依賴

目前有加品項與 complete，沒有先取得 tokenValue 的建車操作。

必補候選（均已在本機快照確認存在）：

| 方法 | 路徑 | 理由 |
|---|---|---|
| POST | `/api/v2/shop/orders` | 建立 cart/order，取得 tokenValue |
| PUT | `/api/v2/shop/orders/{tokenValue}` | 填 email、billingAddress、shippingAddress 等 |
| PATCH | `/api/v2/shop/orders/{tokenValue}/items/{orderItemId}` | 修改 quantity，補正常購物變化 |
| DELETE | `/api/v2/shop/orders/{tokenValue}/items/{orderItemId}` | 移除品項 |
| PATCH | `/api/v2/shop/orders/{tokenValue}/shipments/{shipmentId}` | 保存 shippingMethod |
| PATCH | `/api/v2/shop/orders/{tokenValue}/payments/{paymentId}` | 保存 paymentMethod |

配送／付款可用方法與前置 ID 的查詢可作流程支援，依固定實例與離線付款設定決定。不能把「只讀 payment-methods」當成已選付款方式。即使以 fixtures 預先準備狀態，也必須記錄準備方式，不應把清單稱作自足的完整流程。

若想控制範圍，可把 products detail 的 code/slug 先留一種、單筆地址讀取、重複品項讀取移第二批；verification-request 只在實際啟用時納入。不要硬限制每平台恰好 15 個。

### P1：Bagisto 缺少保存配送與付款的操作

`POST /checkout-orders` 的描述要求地址、配送、付款先保存。原清單只取配送清單，不能替代保存。

| 方法 | 路徑 | 建議 |
|---|---|---|
| POST | `/checkout-shipping-methods` | 補入；保存 shippingMethod |
| GET | `/payment-methods` | 補入或作前置；查可用方式 |
| POST | `/checkout-payment-methods` | 補入；保存 paymentMethod，使用測試／離線方式 |
| POST | `/customers` | 若收集註冊流程則補入；快照內不是 `/customer/register` |
| POST | `/customer-addresses` | 若保留更新地址且非 fixtures 預建，補入建立地址 |
| POST | `/cart-tokens` | 訪客購物時補入；若只做已登入流程可暫緩 |

原始描述提及 `/cart-token` 單數，但快照正式 paths 是 `/cart-tokens` 複數；應以部署測試確認，不能直接照敘述拼 URL。`POST /cart` 是讀取／重算目前車，不能簡化成「每次建立新車」。`checkout-orders` 201 的 redirect=true 分支代表尚待支付跳轉，不代表訂單已建立。

若控制為約 15 個，可暫緩 logout、profile、地址簿 GET/PUT，把位置留給註冊與保存配送／付款；地址文字仍由 checkout-addresses 蒐集。這是候選取捨，最終依實例成功流程確認。

### P2：Shopware 缺更新品項、情境與訂單查詢

| 方法 | 路徑 | 建議 |
|---|---|---|
| PATCH | `/checkout/cart/line-item` | 補入；更新 quantity |
| PATCH | `/context` | 補入；切換配送、付款、地址等情境 |
| POST | `/order` | 建議補入，三平台都涵蓋訂單查詢 |

`GET /checkout/gateway` 是結帳可用性評估／擴充，不是保存配送付款資料。可移第二批，不能當 `/context` 的替代。若要精簡，可暫緩 `/product-listing/{categoryId}` 的重複 catalog 情境或 logout。配送／付款 ID 可以來自固定 fixture，但需明確保存與驗證。

### P2：契約版本與正常採樣覆蓋

- Bagisto 快照 info.version=2.4.10，需固定對應核心版本與 API 套件 commit，不能只看規格標頭就宣稱部署一致。
- Shopware 快照 info.version=6.7.9999999-dev，不宜直接當正式固定版實驗來源，需選可部署 release 並匯出其契約。
- Sylius demo 快照 info.version=0.0.0，不代表任何固定安裝版本；重新由固定實例取得，記錄版本、套件、channel、locale、驗證設定。
- api-contracts/README.md 還寫沒有 Sylius JSON/YAML，但檔案已存在；api-sources 等表也需同步。不要把尚未部署欄位填成已驗證。
- 這 45 個候選對正常與 SQLi/XSS 的部分輸入有用，不足以自動支援 CMDi／路徑穿越。selected-apis.md 寫第一版三類，feature-plan.md 卻寫五分類；應固定第一版 label contract。沒有合理樣本的類別不得填充假情境。
- 敏感值排除正確，但單純長度／型別異常、普通 4xx 不能自動標為攻擊；也不可把「任何非法權限修改」塞到四類注入之一。
- Sylius 有 JSON-LD 與 application/merge-patch+json，Bagisto 有動態屬性 query，Shopware 有 criteria/filter/associations。必須保留合法巢狀正常案例，不能把不熟悉欄位一律視為攻擊。

### P2：Medusa 測試範圍已改變

- 新專案為 2.22.4，不再是舊目錄的 2.21.0。根目錄的舊 77 操作說明需重新對照當前 bundled spec。
- 前台現在使用 `POST /store/search`，它是新增的操作；若仍只測舊 GET /store/products，就無法驗證現行搜尋流程。
- 79 是當前靜態規格的數字，不等於所有操作都已啟用或實測成功。MFA／支付／語系等仍依部署設定。
- README 已說明目前 logger 在框架前置驗證後；若未來只靠這個 logger 蒐集外部測試資料，缺金鑰、無效 JSON 等提前拒絕案例會缺失。應由測試端另存去敏感請求與結果，與 server log 對帳；這是採樣設計問題，非本次已修改項目。

## 選用原則與執行順序

1. 先修抽出契約的遮罩錯誤與 security 繼承／引用，不改原始官方快照。
2. 固定三平台版本與本機隔離實例；不向第三方官方 Demo 發送攻擊或狀態變更測試。
3. 每平台先打通正常流程：搜尋 → 註冊／登入 → 建車 → 加／改／刪品項 → 地址 → 配送／離線付款 → 建單 → 查單。
4. 若流程支援端點不算主要訓練情境，也要列入前置準備清單，保留狀態生成方式。端點數不需相等，以業務事件與樣本比例控制比較。
5. 流程成功後才在合理欄位加入已審核攻擊嘗試。做非惡意錯誤、特殊字元、跨語言、不同格式等正常案例。
6. 固定三類或五類的實驗範圍，分離來源、模板、批次，做平台留一與 Medusa 外部測試。沒有實證不能承諾所有電商有效。

## 45 個原選定操作逐項判斷

以下是對現有清單的靜態審查，沒有把「契約存在」當成「實例可用」。

| 平台 | 方法與路徑 | 判斷 | 理由 |
|---|---|---|---|
| bagisto | `POST /add-product-in-cart` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| bagisto | `POST /cart` | 保留：正常狀態流程 | 不是單純建立購物車；描述是讀取／重算目前車，依 Bearer 識別。訪客另需 /cart-tokens。 |
| bagisto | `POST /checkout-addresses` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| bagisto | `POST /checkout-orders` | 保留但先補依賴 | 先保存地址、配送方式、付款方式；201 仍可能要求支付跳轉，不等於訂單已建立。 |
| bagisto | `GET /checkout-shipping-methods` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| bagisto | `GET /customer-addresses` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| bagisto | `PUT /customer-addresses/{id}` | 保留或移第二批 | 沒有 POST /customer-addresses，需事先建立地址；若精簡成 15 個，可暫緩地址簿 CRUD，保留 checkout-addresses。 |
| bagisto | `GET /customer-orders` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| bagisto | `GET /customer-profile` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| bagisto | `POST /customer/login` | 保留；先修契約 | 拆分檔 password schema 被遮罩成字串；應還原結構，只遮罩實際資料／example 值。 |
| bagisto | `POST /customer/logout` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| bagisto | `GET /products` | 保留：內容辨識核心 | 搜尋與動態屬性篩選需包含合法任意屬性；未知參數不能一律標攻擊。 |
| bagisto | `GET /products/{id}` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| bagisto | `POST /remove-cart-item` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| bagisto | `POST /update-cart-item` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /account/address` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /account/customer` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /account/list-address` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /account/login` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /account/logout` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /account/register` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `GET /checkout/cart` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /checkout/cart/line-item` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /checkout/cart/line-item/delete` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `GET /checkout/gateway` | 輔助／可移第二批 | 評估結帳可用方式，不是保存配送付款情境，也不是訂單查詢。 |
| shopware | `POST /checkout/order` | 保留但先補依賴 | 需有效 ContextToken、購物車與合法顧客／配送付款狀態；缺 PATCH /context。 |
| shopware | `POST /product` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /product-listing/{categoryId}` | 保留或精簡 | 與 /product、/search 同屬 catalog，可暫緩其中一個，把名額留給更新品項與 context。 |
| shopware | `POST /product/{productId}` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| shopware | `POST /search` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `GET /api/v2/shop/addresses` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `POST /api/v2/shop/addresses` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `GET /api/v2/shop/addresses/{id}` | 保留或精簡 | 與地址清單可形成重複讀取；優先補購物車建立、更新與移除。 |
| sylius | `POST /api/v2/shop/customers` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `POST /api/v2/shop/customers/token` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `POST /api/v2/shop/customers/verification-request` | 條件式／第二批 | 信箱通知與驗證受部署設定影響，不是三平台正常購物的共通必備流程。 |
| sylius | `GET /api/v2/shop/orders` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `GET /api/v2/shop/orders/{tokenValue}` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `PATCH /api/v2/shop/orders/{tokenValue}/complete` | 保留但先補結帳 | 需地址、配送與付款狀態；PATCH 通常採 application/merge-patch+json，依快照與部署核對。 |
| sylius | `GET /api/v2/shop/orders/{tokenValue}/items` | 保留或精簡 | 可測試品項列表；先確認與 GET order 回傳的重疊，別犧牲必需寫入流程。 |
| sylius | `POST /api/v2/shop/orders/{tokenValue}/items` | 保留但先補建車 | 需先 POST /api/v2/shop/orders 取得 tokenValue；不能每次捏造識別碼。 |
| sylius | `GET /api/v2/shop/payment-methods` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `GET /api/v2/shop/products` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `GET /api/v2/shop/products-by-slug/{slug}` | 保留 | 屬選定正常業務流程；分類效果仍需資料、合理攻擊位置與實例測試。 |
| sylius | `GET /api/v2/shop/products/{code}` | 保留或精簡 | 與 products-by-slug 都可作 detail；若缺額，先保留其中一種，另一種作額外路徑案例。 |

## 確認程度

已完成：45 操作對原始快照存在性、去除範例後的結構比對、參數說明對認證需求、流程依賴與版本文件的靜態檢查。

未完成：三平台部署、正常購物實測、模型訓練、偵測效果及負載測試；不能把本報告當這些項目已通過。

## 官方核對入口

- Shopware 情境設定：https://developer.shopware.com/frontends/frontends-recipes/context/session-context.html
- Shopware 訂單查詢：https://developer.shopware.com/frontends/frontends-recipes/account/order-history.html
- 其餘方法／路徑與欄位建議直接來自本機保存的原始 OpenAPI；最終以固定版本實例驗證。

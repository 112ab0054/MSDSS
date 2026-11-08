# shopware API 契約參數

> 本文件直接依各 operation JSON 與來源 OpenAPI 重新整理。可輸入值只會列出契約已定義的 enum、預設值、範例與限制；未列固定值時，會明確說明資料型別。

## 01. 取得購物車 API

`GET /checkout/cart`

**operationId：** readCart  
**來源檔案：** get-checkout-cart.json

**API 涵義：** 回傳目前購物車或建立後的購物車。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 購物車。 |
| 401 | 缺少 `sw-access-key` header。 |
## 02. 建立顧客地址 API

`POST /account/address`

**operationId：** createCustomerAddress  
**來源檔案：** post-account-address.json

**API 涵義：** 回傳新建立的顧客地址。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-context-token | 依認證組合 | string | 識別匿名或已登入顧客的購物情境；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由購物情境取得。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| countryId | 必填 | string | 契約未列固定值。 | 國家識別碼。 |
| countryStateId | 選填 | string | 契約未列固定值。 | 州或省識別碼。 |
| salutationId | 選填 | string | 契約未列固定值。 | 稱謂識別碼。 |
| firstName | 必填 | string | 契約未列固定值。 | 名字。 |
| lastName | 必填 | string | 契約未列固定值。 | 姓氏。 |
| zipcode | 必填 | string | 最多字元數：`50`。 | 郵遞區號；是否必須填寫也受國家設定影響。 |
| city | 必填 | string | 契約未列固定值。 | 城市。 |
| accountType | 選填 | string | 固定值：`private`、`business`。 | 地址所屬的帳戶類型。 |
| company | 選填 | string | 契約未列固定值；`accountType` 為 `business` 時必須提供。 | 公司名稱。 |
| street | 必填 | string | 契約未列固定值。 | 街道地址。 |
| department | 選填 | string | 契約未列固定值。 | 部門。 |
| title | 選填 | string | 契約未列固定值。 | 地址或顧客的稱號。 |
| phoneNumber | 選填 | string | 契約未列固定值；是否必填受商店設定影響。 | 電話號碼。 |
| additionalAddressLine1 | 選填 | string | 契約未列固定值；是否必填受商店設定影響。 | 地址補充行一。 |
| additionalAddressLine2 | 選填 | string | 契約未列固定值；是否必填受商店設定影響。 | 地址補充行二。 |
| customFields | 選填 | object | 可輸入物件；契約未列固定欄位。 | 顧客地址的自訂欄位。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 契約未提供回應說明。 |
| 400 | 此狀態表示 API 回應了「The submitted address data failed validation, e.g. a missing required field or a zip code that does not match the selected country」結果。 |
| 401 | 缺少 `sw-access-key` header。 |
| 403 | 目前沒有顧客登入。 |
## 03. 取得顧客資料 API

`POST /account/customer`

**operationId：** readCustomer  
**來源檔案：** post-account-customer.json

**API 涵義：** 回傳目前顧客資料；訪客階段可透過 guest 欄位辨識。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-context-token | 依認證組合 | string | 識別匿名或已登入顧客的購物情境；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由購物情境取得。 |
| header | sw-include-search-info | 選填 | string | 固定值：`0`、`1`<br>預設值：`"1"` | 是否在回應中包含搜尋資訊。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| page | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 分頁頁碼。 |
| term | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋或查詢文字。 |
| limit | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 限制回傳資料的筆數。 |
| filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| ids | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `ids` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋文字。 |
| associations | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `associations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| post-filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `post-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| sort | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `sort` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| aggregations | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| grouping | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `grouping` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| total-count-mode | 選填 | string | 預設值：`"none"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `total-count-mode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| includes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `includes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| excludes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `excludes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Returns the logged in customer, also for guest sessions. Check for the value of `guest` field to see whether the customer is a guest」結果。 |
| 400 | 此狀態表示 API 回應了「The `Criteria` sent with the request is invalid, e.g. an unknown filter field, sorting field or association」結果。 |
| 401 | 缺少 `sw-access-key` header。 |
| 403 | 目前沒有顧客登入。 |
## 04. 查詢顧客地址 API

`POST /account/list-address`

**operationId：** listAddress  
**來源檔案：** post-account-list-address.json

**API 涵義：** 回傳符合 Criteria 條件的顧客地址。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-context-token | 依認證組合 | string | 識別匿名或已登入顧客的購物情境；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由購物情境取得。 |
| header | sw-include-search-info | 選填 | string | 固定值：`0`、`1`<br>預設值：`"1"` | 是否在回應中包含搜尋資訊。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| page | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 分頁頁碼。 |
| term | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋或查詢文字。 |
| limit | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 限制回傳資料的筆數。 |
| filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| ids | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `ids` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋文字。 |
| associations | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `associations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| post-filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `post-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| sort | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `sort` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| aggregations | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| fields | 選填 | array | 可輸入 array值；契約未列出固定值。 | 指定回應要回傳的欄位名稱陣列。 |
| grouping | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `grouping` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| total-count-mode | 選填 | string | 預設值：`"none"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `total-count-mode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| includes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `includes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| excludes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `excludes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 契約未提供回應說明。 |
| 400 | 此狀態表示 API 回應了「The `Criteria` sent with the request is invalid, e.g. an unknown filter field, sorting field or association」結果。 |
| 401 | 缺少 `sw-access-key` header。 |
| 403 | 目前沒有顧客登入。 |
## 05. 顧客登入 API

`POST /account/login`

**operationId：** loginCustomer  
**來源檔案：** post-account-login.json

**API 涵義：** 登入成功時回傳顧客登入結果與情境 token。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object 或 object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| email | 分支成立時必填 | string | 可輸入字串；契約未列固定字串清單。 | 顧客電子郵件地址。 |
| password | 分支成立時必填 | string | 契約未列固定值；輸入字串。 | 顧客密碼；屬敏感資料，不應寫入模型或一般日誌。 |
| username | 分支成立時必填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `username` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 契約未提供回應說明。 |
| 401 | 此狀態表示 API 回應了「If credentials are incorrect an error is returned」結果。 |
| 429 | 此狀態表示 API 回應了「Too many failed login attempts for this email address or client IP. The `Retry-After` window is contained in the error」結果。 |
## 06. 顧客登出 API

`POST /account/logout`

**operationId：** logoutCustomer  
**來源檔案：** post-account-logout.json

**API 涵義：** 顧客已成功登出。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-context-token | 依認證組合 | string | 識別匿名或已登入顧客的購物情境；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由購物情境取得。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 契約未提供回應說明。 |
| 401 | 缺少 `sw-access-key` header。 |
| 403 | 契約未提供回應說明。 |
## 07. 註冊顧客 API

`POST /account/register`

**operationId：** register  
**來源檔案：** post-account-register.json

**API 涵義：** 顧客註冊成功。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`

請求本文是單一 JSON 物件；契約另外以三組 `anyOf` 條件限制欄位組合：

1. 地址條件：提供 `billingAddress`，或提供 `shippingAddress`、`firstName`、`lastName`。
2. 顧客類型條件：`guest=true`，或提供 `password`。
3. 帳戶類型條件：未提供 `accountType`（預設為 `private`），或提供 `accountType=business`。

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| email | 必填 | string | 契約未列固定值。 | 顧客電子郵件地址；訪客註冊時也用於識別顧客。 |
| billingAddress | 帳單地址分支成立時必填 | object | 依 `CustomerAddressBody` 結構填寫。 | 顧客帳單地址；未提供時可能依配送地址補足。 |
| shippingAddress | 配送地址分支成立時必填 | object | 依 `CustomerAddressBody` 結構填寫。 | 顧客配送地址；在相應分支中也可作為帳單地址。 |
| firstName | 配送地址分支成立時必填 | string | 可輸入字串；契約未列固定字串清單。 | 顧客名字。 |
| lastName | 配送地址分支成立時必填 | string | 可輸入字串；契約未列固定字串清單。 | 顧客姓氏。 |
| guest | 訪客分支成立時必填 | boolean | 預設值：`false`；布林可填值：`true`、`false` | 是否建立訪客顧客；`true` 時可不提供密碼。 |
| password | 分支成立時必填 | string | 契約未列固定值；輸入字串。 | 顧客密碼；訪客顧客不需要提供。屬敏感資料，不應寫入模型或一般日誌。 |
| accountType | 選填 | string | 固定值：`private`、`business`；預設值：`private`。 | 顧客帳戶類型。 |
| company | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 公司名稱。 |
| vatIds | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `vatIds` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 成功。 |
| 400 | 此狀態表示 API 回應了「The submitted registration data failed validation, e.g. a missing required field, an email address that is already registered or an unknown country」結果。 |
| 401 | 缺少 `sw-access-key` header。 |
## 08. 移除購物車商品 API

`POST /checkout/cart/line-item/delete`

**operationId：** removeLineItem  
**來源檔案：** post-checkout-cart-line-item-delete.json

**API 涵義：** 回傳移除商品後的更新購物車。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| ids | 必填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `ids` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「The updated cart」結果。 |
| 401 | 缺少 `sw-access-key` header。 |
| 404 | 此狀態表示 API 回應了「One of the given ids does not reference a line item of the current cart」結果。 |
## 09. 新增商品至購物車 API

`POST /checkout/cart/line-item`

**operationId：** addLineItem  
**來源檔案：** post-checkout-cart-line-item.json

**API 涵義：** 回傳加入商品後的更新購物車。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| items | 必填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `items` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「The updated cart」結果。 |
| 400 | 契約未提供回應說明。 |
| 401 | 缺少 `sw-access-key` header。 |
| 429 | 此狀態表示 API 回應了「Too many repeated line item additions. Wait for the number of seconds provided in the error before retrying」結果。 |
## 10. 建立訂單 API

`POST /checkout/order`

**operationId：** createOrder  
**來源檔案：** post-checkout-order.json

**API 涵義：** 回傳從購物車建立的訂單。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-context-token | 依認證組合 | string | 識別匿名或已登入顧客的購物情境；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由購物情境取得。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| customerComment | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `customerComment` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| affiliateCode | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `affiliateCode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| campaignCode | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `campaignCode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 訂單。 |
| 400 | 此狀態表示 API 回應了「The cart cannot be turned into an order, e.g. because it is empty」結果。 |
| 401 | 缺少 `sw-access-key` header。 |
| 403 | 目前沒有顧客登入。 |
| 409 | 此狀態表示 API 回應了「The `hash` sent by the client does not match the current cart content, so the cart changed since it was last read」結果。 |
## 11. 查詢分類商品 API

`POST /product-listing/{categoryId}`

**operationId：** readProductListing  
**來源檔案：** post-product-listing-categoryid.json

**API 涵義：** 回傳指定分類的商品清單與清單顯示所需資料。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| path | categoryId | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `categoryId` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | p | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 分頁頁碼。 |
| header | sw-include-seo-urls | 選填 | boolean | 可輸入 boolean值；契約未列出固定值。 | 是否在回應中包含 SEO 網址。 |
| header | sw-include-search-info | 選填 | string | 固定值：`0`、`1`<br>預設值：`"1"` | 是否在回應中包含搜尋資訊。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object 或 object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| page | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 分頁頁碼。 |
| term | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋或查詢文字。 |
| limit | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 限制回傳資料的筆數。 |
| filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| ids | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `ids` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋文字。 |
| associations | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `associations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| post-filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `post-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| sort | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `sort` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| aggregations | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| fields | 選填 | array | 可輸入 array值；契約未列出固定值。 | 指定回應要回傳的欄位名稱陣列。 |
| grouping | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `grouping` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| total-count-mode | 選填 | string | 預設值：`"none"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `total-count-mode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| includes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `includes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| excludes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `excludes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| order | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `order` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| p | 選填 | integer | 預設值：`1` | 分頁頁碼。 |
| manufacturer | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `manufacturer` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| min-price | 選填 | integer | 預設值：`0`<br>最小值：0 | 價格範圍的最小值。 |
| max-price | 選填 | integer | 預設值：`0`<br>最小值：0 | 價格範圍的最大值。 |
| rating | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 參數 `rating` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shipping-free | 選填 | boolean | 預設值：`false` | 參數 `shipping-free` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| properties | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `properties` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| manufacturer-filter | 選填 | boolean | 預設值：`true` | 參數 `manufacturer-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| price-filter | 選填 | boolean | 預設值：`true` | 價格或價格範圍條件。 |
| rating-filter | 選填 | boolean | 預設值：`true` | 參數 `rating-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shipping-free-filter | 選填 | boolean | 預設值：`true` | 參數 `shipping-free-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| property-filter | 選填 | boolean | 預設值：`true` | 參數 `property-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| property-whitelist | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `property-whitelist` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| reduce-aggregations | 選填 | object 或 object | 可輸入 object 或 object值；契約未列出固定值。 | 參數 `reduce-aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| no-aggregations | 選填 | object 或 object | 可輸入 object 或 object值；契約未列出固定值。 | 參數 `no-aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| only-aggregations | 選填 | object 或 object | 可輸入 object 或 object值；契約未列出固定值。 | 是否只回傳彙總結果。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Returns a product listing containing all products and additional fields to display a listing」結果。 |
| 400 | 此狀態表示 API 回應了「The `Criteria` sent with the request is invalid, e.g. an unknown filter field, sorting field or association」結果。 |
| 401 | 缺少 `sw-access-key` header。 |
| 404 | 此狀態表示 API 回應了「No category exists for the given `categoryId` in this sales channel」結果。 |
## 12. 取得單一商品 API

`POST /product/{productId}`

**operationId：** readProductDetail  
**來源檔案：** post-product-productid.json

**API 涵義：** 回傳指定商品、變體群組與選項資料。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| path | productId | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 商品的唯一識別碼。 |
| header | sw-include-seo-urls | 選填 | boolean | 可輸入 boolean值；契約未列出固定值。 | 是否在回應中包含 SEO 網址。 |
| header | sw-include-search-info | 選填 | string | 固定值：`0`、`1`<br>預設值：`"1"` | 是否在回應中包含搜尋資訊。 |
| query | skipConfigurator | 選填 | boolean | 可輸入 boolean值；契約未列出固定值。 | 參數 `skipConfigurator` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | skipCmsPage | 選填 | boolean | 可輸入 boolean值；契約未列出固定值。 | 參數 `skipCmsPage` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object 或 object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| slots | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `slots` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| page | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 分頁頁碼。 |
| term | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋或查詢文字。 |
| limit | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 限制回傳資料的筆數。 |
| filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| ids | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `ids` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋文字。 |
| associations | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `associations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| post-filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `post-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| sort | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `sort` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| aggregations | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| grouping | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `grouping` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| total-count-mode | 選填 | string | 預設值：`"none"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `total-count-mode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| includes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `includes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| excludes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `excludes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Product information along with variant groups and options」結果。 |
| 400 | 此狀態表示 API 回應了「The `Criteria` sent with the request is invalid, e.g. an unknown filter field, sorting field or association」結果。 |
| 401 | 缺少 `sw-access-key` header。 |
| 404 | 此狀態表示 API 回應了「No product exists for the given `productId` in this sales channel」結果。 |
## 13. 依條件查詢商品 API

`POST /product`

**operationId：** readProduct  
**來源檔案：** post-product.json

**API 涵義：** 回傳符合 Criteria 的商品清單。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-include-search-info | 選填 | string | 固定值：`0`、`1`<br>預設值：`"1"` | 是否在回應中包含搜尋資訊。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| page | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 分頁頁碼。 |
| term | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋或查詢文字。 |
| limit | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 限制回傳資料的筆數。 |
| filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| ids | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `ids` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋文字。 |
| associations | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `associations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| post-filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `post-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| sort | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `sort` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| aggregations | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| fields | 選填 | array | 可輸入 array值；契約未列出固定值。 | 指定回應要回傳的欄位名稱陣列。 |
| grouping | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `grouping` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| total-count-mode | 選填 | string | 預設值：`"none"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `total-count-mode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| includes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `includes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| excludes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `excludes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 契約未提供回應說明。 |
| 400 | 此狀態表示 API 回應了「The `Criteria` sent with the request is invalid, e.g. an unknown filter field, sorting field or association」結果。 |
| 401 | 缺少 `sw-access-key` header。 |
## 14. 搜尋商品 API

`POST /search`

**operationId：** searchPage  
**來源檔案：** post-search.json

**API 涵義：** 回傳商品搜尋與清單結果。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| query | p | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 分頁頁碼。 |
| header | sw-include-seo-urls | 選填 | boolean | 可輸入 boolean值；契約未列出固定值。 | 是否在回應中包含 SEO 網址。 |
| header | sw-include-search-info | 選填 | string | 固定值：`0`、`1`<br>預設值：`"1"` | 是否在回應中包含搜尋資訊。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object 或 object 或 object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| search | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 商品搜尋文字。 |
| page | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 分頁頁碼。 |
| term | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋或查詢文字。 |
| limit | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 限制回傳資料的筆數。 |
| filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| ids | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `ids` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋文字。 |
| associations | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `associations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| post-filter | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `post-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| sort | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `sort` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| aggregations | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| fields | 選填 | array | 可輸入 array值；契約未列出固定值。 | 指定回應要回傳的欄位名稱陣列。 |
| grouping | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `grouping` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| total-count-mode | 選填 | string | 預設值：`"none"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `total-count-mode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| includes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `includes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| excludes | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `excludes` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| order | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `order` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| p | 選填 | integer | 預設值：`1` | 分頁頁碼。 |
| manufacturer | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `manufacturer` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| min-price | 選填 | integer | 預設值：`0`<br>最小值：0 | 價格範圍的最小值。 |
| max-price | 選填 | integer | 預設值：`0`<br>最小值：0 | 價格範圍的最大值。 |
| rating | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 參數 `rating` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shipping-free | 選填 | boolean | 預設值：`false` | 參數 `shipping-free` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| properties | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `properties` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| manufacturer-filter | 選填 | boolean | 預設值：`true` | 參數 `manufacturer-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| price-filter | 選填 | boolean | 預設值：`true` | 價格或價格範圍條件。 |
| rating-filter | 選填 | boolean | 預設值：`true` | 參數 `rating-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shipping-free-filter | 選填 | boolean | 預設值：`true` | 參數 `shipping-free-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| property-filter | 選填 | boolean | 預設值：`true` | 參數 `property-filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| property-whitelist | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `property-whitelist` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| reduce-aggregations | 選填 | object 或 object | 可輸入 object 或 object值；契約未列出固定值。 | 參數 `reduce-aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| no-aggregations | 選填 | object 或 object | 可輸入 object 或 object值；契約未列出固定值。 | 參數 `no-aggregations` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| only-aggregations | 選填 | object 或 object | 可輸入 object 或 object值；契約未列出固定值。 | 是否只回傳彙總結果。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Returns a product listing containing all products and additional fields to display a listing」結果。 |
| 400 | 此狀態表示 API 回應了「The `search` parameter is missing, or the `Criteria` sent with the request is invalid」結果。 |
| 401 | 缺少 `sw-access-key` header。 |


<!-- MSDSS_API_EXTENSION_20261108 -->

---

以下為本次增補操作；原第 01–15 節內容保留不變。新增欄位沿用原表格，另補來源認證與巢狀結構；可輸入值列出來源的選項、預設、範例及限制。完整採用規則見 [增補計畫](../../api-extension/plan.md)。
## 15. 更新購物車品項 API

`PATCH /checkout/cart/line-item`

**operationId：** updateLineItem  
**來源檔案：** patch-checkout-cart-line-item.json

**API 涵義：** 更新購物車中的品項，例如修改商品數量。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-language-id | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：來源未宣告本文必填；送出本文時，`items` 與各品項 `id` 必填。
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| items | 送出本文時必填 | array | 每個元素包含要更新的購物車品項資料。 | 要更新的購物車品項清單。 |
| items[].id | 每個品項必填 | string | 使用目前購物車回應中的品項識別碼。 | 要更新的購物車品項識別碼。 |
| items[].quantity | 選填 | integer | 必須是正整數；數量限制依商品與購物車規則。 | 商品數量。 |
| items[].type | 選填 | 依契約 | 至少符合一種結構第 1 組：固定值：`product`、`credit`、`custom`、`promotion`、`container`、`discount`、`quantity`<br>至少符合一種結構第 2 組：可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 品項的實體類型，例如商品或促銷；可用類型依購物車處理器支援情況。 |
| items[].referencedId | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 品項關聯的資料識別碼，例如商品識別碼；依品項類型填寫。 |
| items[].label | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 品項顯示名稱。 |
| items[].payload | 選填 | object | 可輸入物件；具名子欄位見下表，契約未列固定選項。 | 品項的附加鍵值資料；允許的內容依品項處理器與實例規則。 |
| items[].stackable | 選填 | boolean | 布林可填值：`true`、`false` | 是否允許合併或累加此品項數量。 |
| items[].removable | 選填 | boolean | 布林可填值：`true`、`false` | 是否允許移除此品項。 |
| items[].coverId | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 品項封面媒體的識別碼。 |
| items[].priceDefinition | 選填 | object | 可輸入物件；具名子欄位見下表，契約未列固定選項。 | 品項的價格定義物件，欄位見下列子欄位。 |
| items[].priceDefinition.type | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 價格定義類型；來源未列固定選項，依實例支援的類型填寫。 |
| items[].priceDefinition.price | 選填 | number | 可輸入數值；契約未列固定範圍。 | 價格金額。 |
| items[].priceDefinition.percentage | 選填 | number | 可輸入數值；契約未列固定範圍。 | 百分比數值。 |
| items[].priceDefinition.quantity | 選填 | integer | 可輸入整數；契約未列固定範圍。 | 此價格定義使用的數量。 |
| items[].priceDefinition.isCalculated | 選填 | boolean | 布林可填值：`true`、`false` | 此價格是否已完成計算。 |
| items[].priceDefinition.listPrice | 選填 | number | 可輸入數值；契約未列固定範圍。 | 比較用的原價。 |
| items[].priceDefinition.taxRules | 選填 | array | 每個陣列元素：可輸入物件；具名子欄位見下表，契約未列固定選項。 | 套用此價格的稅務規則清單。 |
| items[].priceDefinition.taxRules[].taxRate | 選填 | number | 可輸入數值；契約未列固定範圍。 | 稅率數值。 |
| items[].priceDefinition.taxRules[].percentage | 選填 | number | 可輸入數值；契約未列固定範圍。 | 此稅務規則的分攤百分比。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 更新後的購物車。 |
| 400 | 品項無法更新，例如數量不是正整數、不是父品項數量的倍數，或品項類型不支援更新。 |
| 401 | 缺少 `sw-access-key` header。 |
| 404 | 提供的品項識別碼不屬於目前購物車。 |
## 16. 更新購物情境設定 API

`PATCH /context`

**operationId：** updateContext  
**來源檔案：** patch-context.json

**API 涵義：** 切換目前購物情境，例如變更語言或貨幣。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-language-id | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| currencyId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 貨幣識別碼。 |
| languageId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 語言識別碼。 |
| billingAddressId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 帳單地址識別碼。 |
| shippingAddressId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 配送地址識別碼。 |
| paymentMethodId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 付款方式識別碼。 |
| shippingMethodId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 配送方式識別碼。 |
| countryId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 國家識別碼。 |
| countryStateId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 州或省識別碼。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 回傳購物情境 token；後續請求使用 `sw-context-token` header。 |
| 400 | 提交的識別碼不是字串，或不屬於目前銷售通路可用的實體。 |
| 401 | 缺少 `sw-access-key` header。 |
| 403 | 未登入顧客卻提交了帳單地址或配送地址識別碼。 |
## 17. 查詢顧客訂單 API

`POST /order`

**operationId：** readOrder  
**來源檔案：** post-order.json

**API 涵義：** 查詢顧客的訂單清單。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-context-token | 依認證組合 | string | 顧客購物情境識別值；屬敏感資料，不應寫入模型或一般日誌。 | 識別目前顧客情境。 |
| header | sw-include-search-info | 選填 | string | 固定值：`0`、`1`；預設值：`1`。 | 是否在回應中包含搜尋資訊。 |
| header | sw-language-id | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 回應使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | 從 storefront session cookie 解析情境。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object 或 object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| filter | 選填 | array | 可使用 `equals` 條件；訪客查詢可使用欄位 `deepLinkCode`。 | 訂單篩選條件。 |
| email | 選填 | string | 契約格式：`email`。 | 訪客訂單驗證使用的顧客電子郵件。 |
| zipcode | 選填 | string | 契約未列固定值。 | 訪客訂單驗證使用的帳單郵遞區號。 |
| login | 選填 | boolean | `true`、`false`。 | 找到訪客訂單時是否在回應標頭提供登入情境 token。 |
| checkPromotion | 選填 | boolean | `true`、`false`。 | 檢查訂單付款方式是否仍可變更。 |
| page | 選填 | integer | 可輸入整數；契約未列固定範圍。 | 搜尋結果的頁碼。 |
| term | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 搜尋關鍵字。 |
| limit | 選填 | integer | 可輸入整數；契約未列固定範圍。 | 每頁最多回傳筆數。 |
| ids | 選填 | array | 每個陣列元素：可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 要查詢的訂單識別碼清單。 |
| query | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 依實體搜尋設定執行的查詢文字。 |
| associations | 選填 | object | 物件鍵為關聯名稱，值為 Criteria 查詢條件物件。可用關聯依實體定義。 | 指定要載入的訂單關聯資料及各關聯的查詢條件。 |
| post-filter | 選填 | array | 物件陣列；依所選結構，type 可為 `contains`、`equalsAny`、`prefix`、`suffix`、`equals`、`multi`、`not`、`range`。各結構的欄位依來源 Filters／SimpleFilter／EqualsFilter／MultiNotFilter／RangeFilter 定義。 | 在不影響彙總統計的情況下篩選訂單結果。 |
| sort | 選填 | array | 物件陣列；可填 field、order、naturalSorting、type；order 固定值：`ASC`、`DESC`，其餘限制依來源 Sort 結構。 | 訂單結果的排序條件。 |
| aggregations | 選填 | array | 物件陣列；依所選結構，type 可為 `avg`、`count`、`max`、`min`、`stats`、`sum`、`entity`、`filter`、`terms`、`histogram`、`range`。其餘欄位依來源 Aggregation 結構。 | 對指定欄位執行彙總統計。 |
| grouping | 選填 | array | 字串陣列；每個元素為用來分組的欄位名稱。契約未列有限選項清單。 | 指定分組使用的欄位名稱。 |
| total-count-mode | 選填 | string | 固定值：`none`、`exact`、`next-pages`<br>預設值：`"none"` | 總筆數計算方式：none 不計算、exact 精確計算、next-pages 計算判斷後續頁面所需的數量。 |
| includes | 選填 | object | 物件格式：`{"實體名稱":["欄位名稱"]}`；若同一欄位也列於 excludes，則不回傳。 | 依實體指定回應包含的欄位；物件鍵為實體名稱，值為欄位名稱陣列。 |
| excludes | 選填 | object | 物件格式：`{"實體名稱":["欄位名稱"]}`。 | 依實體指定回應排除的欄位；物件鍵為實體名稱，值為欄位名稱陣列。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 訂單陣列，以及付款方式是否可變更的指示值。 |
| 400 | Criteria 條件無效。 |
| 401 | 缺少 `sw-access-key` header。 |
| 403 | 未登入顧客且未提供符合的訪客訂單驗證資料。 |
| 429 | 訪客驗證失敗次數過多。 |
## 18. 取得購物情境 API

`GET /context`

**operationId：** readContext  
**來源檔案：** get-context.json

**API 涵義：** 取得目前購物情境，包含顧客群組、貨幣與稅則等資料。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| header | sw-language-id | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 回應使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 目前購物情境，並在回應標頭提供 `sw-context-token`。 |
| 401 | 缺少 `sw-access-key` header。 |
## 19. 查詢付款方式 API

`GET /payment-method`

**operationId：** readPaymentMethodGet  
**來源檔案：** get-payment-method.json

**API 涵義：** 取得目前可用的付款方式。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| query | orderId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 依指定訂單評估目前顧客可用的付款方式。 |
| query | page | 選填 | integer | 契約未列固定值。 | 分頁頁碼。 |
| query | limit | 選填 | integer | 契約未列固定值。 | 限制回傳筆數。 |
| query | term | 選填 | string | 契約未列固定值。 | 查詢文字。 |
| query | filter[] | 選填 | array | Criteria 篩選條件。 | 篩選付款方式。 |
| query | ids[] | 選填 | array | Criteria 識別碼清單。 | 指定付款方式識別碼。 |
| query | sort[] | 選填 | array | Criteria 排序條件。 | 排序結果。 |
| query | associations | 選填 | object | Criteria 關聯資料。 | 載入付款方式關聯資料。 |
| query | total-count-mode | 選填 | string | 預設值：`none`；契約未列完整固定值清單。 | 控制總筆數計算方式。 |
| query | query | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 依實體搜尋設定執行的查詢文字。 |
| query | post-filter[] | 選填 | array | 物件陣列；依所選結構，type 可為 `contains`、`equalsAny`、`prefix`、`suffix`、`equals`、`multi`、`not`、`range`。各結構的欄位依來源 Filters／SimpleFilter／EqualsFilter／MultiNotFilter／RangeFilter 定義。 | 只篩選回傳結果，不影響彙總統計。 |
| query | aggregations[] | 選填 | array | 物件陣列；依所選結構，type 可為 `avg`、`count`、`max`、`min`、`stats`、`sum`、`entity`、`filter`、`terms`、`histogram`、`range`。其餘欄位依來源 Aggregation 結構。 | 彙總統計條件清單。 |
| query | fields[] | 選填 | array | 字串陣列；每個元素為實體可回傳的欄位名稱。契約未列有限選項清單。 | 要回傳的欄位名稱陣列。 |
| query | grouping[] | 選填 | array | 字串陣列；每個元素為用來分組的欄位名稱。契約未列有限選項清單。 | 分組使用的欄位名稱陣列。 |
| query | includes | 選填 | object | 物件格式：`{"實體名稱":["欄位名稱"]}`；若同一欄位也列於 excludes，則不回傳。 | 依實體指定回應包含的欄位；物件鍵為實體名稱，值為欄位名稱陣列。 |
| query | excludes | 選填 | object | 物件格式：`{"實體名稱":["欄位名稱"]}`。 | 依實體指定回應排除的欄位；物件鍵為實體名稱，值為欄位名稱陣列。 |
| query | _criteria | 選填 | string | 格式：`base64url(gzip(json_encode(criteria)))`；契約格式：`base64url`。<br>範例：`"H4sIAAAAAAAAA6tWykpNzFGyqlbKz8lPTSxRslJKSi0pzSsFAGcQr7sHAAAA"` | 先將查詢條件轉為 JSON，再以 gzip 壓縮、base64url 編碼。可包含此路由的其他查詢參數；其中同名欄位優先於一般查詢參數。 |
| header | sw-language-id | 選填 | string | 正規表示式：`"^[0-9a-f]{32}$"` | 指定回應使用的語言識別碼。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | 固定填 session 時，從前台工作階段 Cookie 取得購物情境；與 sw-context-token 互斥，不可同時送出。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 可用付款方式清單。 |
| 400 | Criteria 條件無效。 |
| 401 | 缺少 `sw-access-key` header。 |
## 20. 查詢配送方式 API

`GET /shipping-method`

**operationId：** readShippingMethodGet  
**來源檔案：** get-shipping-method.json

**API 涵義：** 依條件查詢配送方式。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| query | orderId | 選填 | string | 正規表示式：`^[0-9a-f]{32}$` | 依指定訂單評估目前顧客可用的配送方式。 |
| query | page | 選填 | integer | 契約未列固定值。 | 分頁頁碼。 |
| query | limit | 選填 | integer | 契約未列固定值。 | 限制回傳筆數。 |
| query | term | 選填 | string | 契約未列固定值。 | 查詢文字。 |
| query | filter[] | 選填 | array | Criteria 篩選條件。 | 篩選配送方式。 |
| query | ids[] | 選填 | array | Criteria 識別碼清單。 | 指定配送方式識別碼。 |
| query | sort[] | 選填 | array | Criteria 排序條件。 | 排序結果。 |
| query | associations | 選填 | object | Criteria 關聯資料。 | 載入配送方式的價格、配送時間等關聯資料。 |
| query | total-count-mode | 選填 | string | 預設值：`none`；契約未列完整固定值清單。 | 控制總筆數計算方式。 |
| query | query | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 依實體搜尋設定執行的查詢文字。 |
| query | post-filter[] | 選填 | array | 物件陣列；依所選結構，type 可為 `contains`、`equalsAny`、`prefix`、`suffix`、`equals`、`multi`、`not`、`range`。各結構的欄位依來源 Filters／SimpleFilter／EqualsFilter／MultiNotFilter／RangeFilter 定義。 | 只篩選回傳結果，不影響彙總統計。 |
| query | aggregations[] | 選填 | array | 物件陣列；依所選結構，type 可為 `avg`、`count`、`max`、`min`、`stats`、`sum`、`entity`、`filter`、`terms`、`histogram`、`range`。其餘欄位依來源 Aggregation 結構。 | 彙總統計條件清單。 |
| query | fields[] | 選填 | array | 字串陣列；每個元素為實體可回傳的欄位名稱。契約未列有限選項清單。 | 要回傳的欄位名稱陣列。 |
| query | grouping[] | 選填 | array | 字串陣列；每個元素為用來分組的欄位名稱。契約未列有限選項清單。 | 分組使用的欄位名稱陣列。 |
| query | includes | 選填 | object | 物件格式：`{"實體名稱":["欄位名稱"]}`；若同一欄位也列於 excludes，則不回傳。 | 依實體指定回應包含的欄位；物件鍵為實體名稱，值為欄位名稱陣列。 |
| query | excludes | 選填 | object | 物件格式：`{"實體名稱":["欄位名稱"]}`。 | 依實體指定回應排除的欄位；物件鍵為實體名稱，值為欄位名稱陣列。 |
| query | _criteria | 選填 | string | 格式：`base64url(gzip(json_encode(criteria)))`；契約格式：`base64url`。<br>範例：`"H4sIAAAAAAAAA6tWykpNzFGyqlbKz8lPTSxRslJKSi0pzSsFAGcQr7sHAAAA"` | 先將查詢條件轉為 JSON，再以 gzip 壓縮、base64url 編碼。可包含此路由的其他查詢參數；其中同名欄位優先於一般查詢參數。 |
| header | sw-language-id | 選填 | string | 正規表示式：`"^[0-9a-f]{32}$"` | 指定回應使用的語言識別碼。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | 固定填 session 時，從前台工作階段 Cookie 取得購物情境；與 sw-context-token 互斥，不可同時送出。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 可用配送方式清單。 |
| 400 | Criteria 條件無效。 |
| 401 | 缺少 `sw-access-key` header。 |

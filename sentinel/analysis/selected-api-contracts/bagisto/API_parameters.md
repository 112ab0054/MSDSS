# bagisto API 契約參數

> 本文件直接依各 operation JSON 與來源 OpenAPI 重新整理。可輸入值只會列出契約已定義的 enum、預設值、範例與限制；未列固定值時，會明確說明資料型別。

## 01. 取得購物車配送方式 API

`GET /checkout-shipping-methods`

**operationId：** api_apishopcheckout-shipping-methods_get_collection  
**來源檔案：** get-checkout-shipping-methods.json

**API 涵義：** 回傳目前已認證顧客購物車可用的配送方式與費率。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 可用的配送方式。 |

## 02. 取得顧客地址清單 API

`GET /customer-addresses`

**operationId：** api_apishopcustomer-addresses_get_collection  
**來源檔案：** get-customer-addresses.json

**API 涵義：** 回傳目前已認證顧客儲存的地址清單。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| query | sort | 選填 | string | 固定值：`id`、`created_at`、`id-asc`、`id-desc`、`created_at-asc`、`created_at-desc` | 參數 `sort` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | order | 選填 | string | 固定值：`asc`、`desc` | 參數 `order` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | page | 選填 | integer | 預設值：`1` | 分頁頁碼。 |
| query | per_page | 選填 | integer | 預設值：`10`<br>最小值：0<br>最大值：50 | 每頁回傳筆數。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 顧客地址清單。 |

## 03. 取得顧客訂單清單 API

`GET /customer-orders`

**operationId：** api_apishopcustomer-orders_get_collection  
**來源檔案：** get-customer-orders.json

**API 涵義：** 回傳顧客訂單資源集合。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| query | page | 選填 | integer | 預設值：`1` | 分頁頁碼。 |
| query | per_page | 選填 | integer | 預設值：`10`<br>最小值：0<br>最大值：50 | 每頁回傳筆數。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「CustomerOrder collection」結果。 |

## 04. 取得顧客個人資料 API

`GET /customer-profile`

**operationId：** api_apishopcustomer-profile_get_collection  
**來源檔案：** get-customer-profile.json

**API 涵義：** 回傳目前已認證顧客的個人資料。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Authenticated customer profile」結果。 |

## 05. 取得單一商品及關聯資料 API

`GET /products/{id}`

**operationId：** api_apishopproducts_id_get  
**來源檔案：** get-products-id.json

**API 涵義：** 回傳包含所有內嵌關聯資料的單一商品。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| path | id | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 資源的唯一識別碼。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「The product with all relations embedded inline」結果。 |
| 404 | 此狀態表示 API 回應了「Product not found」結果。 |

## 06. 搜尋及篩選商品 API

`GET /products`

**operationId：** api_apishopproducts_get_collection  
**來源檔案：** get-products.json

**API 涵義：** 回傳符合搜尋、篩選與排序條件的分頁商品清單。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| query | query | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 搜尋文字。 |
| query | suggest | 選填 | string | 固定值：`0`、`1` | 參數 `suggest` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | sort | 選填 | string | 範例：`"name-asc"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `sort` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | order | 選填 | string | 固定值：`asc`、`desc` | 參數 `order` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | page | 選填 | integer | 預設值：`1`<br>範例：`1` | 分頁頁碼。 |
| query | per_page | 選填 | integer | 預設值：`30`<br>範例：`30` | 每頁回傳筆數。 |
| query | type | 選填 | string | 固定值：`simple`、`configurable`、`virtual`、`downloadable`、`bundle`、`grouped`、`booking` | 參數 `type` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | category_id | 選填 | integer | 範例：`2` | 參數 `category_id` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | price | 選填 | string | 範例：`"10,200"`<br>可輸入字串；契約未列固定字串清單。 | 價格或價格範圍條件。 |
| query | price_from | 選填 | number | 可輸入 number值；契約未列出固定值。 | 價格或價格範圍條件。 |
| query | price_to | 選填 | number | 可輸入 number值；契約未列出固定值。 | 價格或價格範圍條件。 |
| query | new | 選填 | boolean | 可輸入 boolean值；契約未列出固定值。 | 參數 `new` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | featured | 選填 | boolean | 可輸入 boolean值；契約未列出固定值。 | 參數 `featured` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | filter | 選填 | object | 範例：`{"brand":"38","color":"3"}` | 參數 `filter` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「A paginated list of products matching the search, filter, and sort criteria」結果。 |

## 07. 新增商品至購物車 API

`POST /add-product-in-cart`

**operationId：** addProduct  
**來源檔案：** post-add-product-in-cart.json

**API 涵義：** 商品已加入購物車，並回傳完整購物車。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| productId | 選填 | integer | 範例：`1` | 商品的唯一識別碼。 |
| quantity | 選填 | integer | 範例：`1` | 要加入或更新的商品數量。 |
| selectedConfigurableOption | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 可配置商品所選的選項。 |
| superAttribute | 選填 | object | 可輸入 object值；契約未列出固定值。 | 可配置商品的屬性選擇。 |
| qty | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `qty` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| bundleOptions | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `bundleOptions` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| bundleOptionQty | 選填 | object | 可輸入 object值；契約未列出固定值。 | 參數 `bundleOptionQty` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| links | 選填 | array | 可輸入 array值；契約未列出固定值。 | 參數 `links` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| booking | 選填 | object | 可輸入 object值；契約未列出固定值。 | 預約商品的預約資料。 |
| specialNote | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 加入購物車時的特別備註。 |
| isBuyNow | 選填 | integer | 可輸入 integer值；契約未列出固定值。 | 參數 `isBuyNow` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 此狀態表示 API 回應了「Product added to cart. Returns the full cart」結果。 |
| 400 | 此狀態表示 API 回應了「Missing/invalid productId or quantity, or product not saleable」結果。 |
| 422 | 驗證錯誤。 |

## 08. 取得目前購物車 API

`POST /cart`

**operationId：** api_apishopcart_post  
**來源檔案：** post-cart.json

**API 涵義：** 回傳目前購物車及其商品、金額、優惠券、配送、付款與地址資料。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 此狀態表示 API 回應了「The cart with items, totals, coupon, and selected shipping/payment」結果。 |
| 400 | 輸入資料無效。 |
| 401 | 此狀態表示 API 回應了「No cart found for the given token, or not authenticated」結果。 |
| 422 | 驗證錯誤。 |

## 09. 儲存購物車地址 API

`POST /checkout-addresses`

**operationId：** api_apishopcheckout-addresses_post  
**來源檔案：** post-checkout-addresses.json

**API 涵義：** 回傳已儲存的結帳地址。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| billingFirstName | 必填 | string | 範例：`"John"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `billingFirstName` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| billingLastName | 必填 | string | 範例：`"Doe"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `billingLastName` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| billingEmail | 必填 | string | 範例：`"john@example.com"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `billingEmail` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| billingCompanyName | 選填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | 參數 `billingCompanyName` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| billingAddress | 必填 | string | 範例：`"123 Main St"`<br>可輸入字串；契約未列固定字串清單。 | 帳單地址。 |
| billingCity | 必填 | string | 範例：`"Los Angeles"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `billingCity` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| billingCountry | 必填 | string | 範例：`"US"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `billingCountry` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| billingState | 必填 | string | 範例：`"CA"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `billingState` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| billingPostcode | 必填 | string | 範例：`"90001"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `billingPostcode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| billingPhoneNumber | 必填 | string | 範例：`"2125551234"`<br>可輸入字串；契約未列固定字串清單。 | 帳單聯絡電話。 |
| useForShipping | 選填 | boolean | 範例：`true` | 是否將帳單地址同時用作配送地址。 |
| shippingFirstName | 選填 | string | 範例：`"Jane"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `shippingFirstName` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shippingLastName | 選填 | string | 範例：`"Doe"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `shippingLastName` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shippingEmail | 選填 | string | 範例：`"jane@example.com"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `shippingEmail` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shippingCompanyName | 選填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | 參數 `shippingCompanyName` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shippingAddress | 選填 | string | 範例：`"456 Oak Ave"`<br>可輸入字串；契約未列固定字串清單。 | 配送地址。 |
| shippingCity | 選填 | string | 範例：`"San Francisco"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `shippingCity` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shippingCountry | 選填 | string | 範例：`"US"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `shippingCountry` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shippingState | 選填 | string | 範例：`"CA"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `shippingState` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shippingPostcode | 選填 | string | 範例：`"94102"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `shippingPostcode` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| shippingPhoneNumber | 選填 | string | 範例：`"4155559876"`<br>可輸入字串；契約未列固定字串清單。 | 配送聯絡電話。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 此狀態表示 API 回應了「Addresses saved successfully」結果。 |
| 400 | 輸入資料無效。 |
| 422 | 驗證錯誤。 |
| 500 | 此狀態表示 API 回應了「Billing address missing/invalid, or no active cart」結果。 |

## 10. 完成結帳並建立訂單 API

`POST /checkout-orders`

**operationId：** api_apishopcheckout-orders_post  
**來源檔案：** post-checkout-orders.json

**API 涵義：** 回傳已建立的訂單，或回傳需要付款導向的結果。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 此狀態表示 API 回應了「Order placed, or a payment redirect is required. Check the `redirect` flag: when it is false the order exists and `orderId` and `incrementId` (the order number to show the shopper) are set; when it is true no order has been created yet and the shopper must be sent to `redirectUrl` to pay — the order is created once the gateway returns」結果。 |
| 400 | 輸入資料無效。 |
| 422 | 驗證錯誤。 |
| 500 | 此狀態表示 API 回應了「Cart not fully prepared (missing addresses/shipping/payment) or checkout failed」結果。 |

## 11. 顧客登入 API

`POST /customer/login`

**operationId：** api_apishopcustomerlogin_post  
**來源檔案：** post-customer-login.json

**API 涵義：** 顧客已完成認證，後續請求使用回傳的 token。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| email | 必填 | string | 範例：`"john@example.com"`<br>可輸入字串；契約未列固定字串清單。 | 顧客電子郵件地址。 |
| password | 必填 |  | 可輸入 未指定值；契約未列出固定值。 | 顧客密碼；屬敏感資料，不應寫入模型或一般日誌。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 此狀態表示 API 回應了「Authenticated. Use `token` as the Bearer token in the Authorization header for subsequent calls」結果。 |
| 400 | 輸入資料無效。 |
| 401 | 此狀態表示 API 回應了「Invalid email or password」結果。 |
| 422 | 驗證錯誤。 |

## 12. 顧客登出 API

`POST /customer/logout`

**operationId：** api_apishopcustomerlogout_post  
**來源檔案：** post-customer-logout.json

**API 涵義：** 顧客已成功登出。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 此狀態表示 API 回應了「Logged out successfully」結果。 |
| 400 | 輸入資料無效。 |
| 422 | 驗證錯誤。 |

## 13. 移除購物車商品 API

`POST /remove-cart-item`

**operationId：** removeItem  
**來源檔案：** post-remove-cart-item.json

**API 涵義：** 回傳移除商品後的更新購物車。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| cartItemId | 必填 | integer | 範例：`1` | 購物車商品項目的唯一識別碼。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 此狀態表示 API 回應了「Updated cart with the item removed」結果。 |
| 400 | 此狀態表示 API 回應了「Missing cartItemId, or item not in cart」結果。 |
| 422 | 驗證錯誤。 |

## 14. 更新購物車商品數量 API

`POST /update-cart-item`

**operationId：** updateItem  
**來源檔案：** post-update-cart-item.json

**API 涵義：** 回傳更新商品數量後的完整購物車。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| cartItemId | 必填 | integer | 範例：`1` | 購物車商品項目的唯一識別碼。 |
| quantity | 必填 | integer | 範例：`3` | 要加入或更新的商品數量。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 此狀態表示 API 回應了「Cart item quantity updated. Returns the full cart」結果。 |
| 400 | 此狀態表示 API 回應了「Missing cartItemId/quantity, or item not in cart」結果。 |
| 422 | 驗證錯誤。 |

## 15. 更新顧客地址 API

`PUT /customer-addresses/{id}`

**operationId：** api_apishopcustomer-addresses_id_put  
**來源檔案：** put-customer-addresses-id.json

**API 涵義：** 回傳更新後的顧客地址。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| path | id | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 資源的唯一識別碼。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例：`""`<br>可輸入字串；契約未列固定字串清單。 | Bagisto Storefront API 公開金鑰。 |
| header | X-Locale | 選填 | string | 範例：`"en"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 回應資料使用的語系。 |
| header | X-Channel | 選填 | string | 範例：`"default"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 商品、價格與庫存所屬的銷售通路。 |
| header | X-Currency | 選填 | string | 範例：`"USD"`<br>可輸入字串；契約未列固定字串清單。 | Bagisto 價格使用的貨幣。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| firstName | 選填 | string | 範例：`"John"`<br>可輸入字串；契約未列固定字串清單。 | 名字。 |
| lastName | 選填 | string | 範例：`"Doe"`<br>可輸入字串；契約未列固定字串清單。 | 姓氏。 |
| companyName | 選填 | string | 範例：`"Acme Inc."`<br>可輸入字串；契約未列固定字串清單。 | 參數 `companyName` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| vatId | 選填 | string | 範例：`"GB123456789"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `vatId` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| email | 選填 | string | 範例：`"john@example.com"`<br>可輸入字串；契約未列固定字串清單。 | 顧客電子郵件地址。 |
| phone | 選填 | string | 範例：`"1234567890"`<br>可輸入字串；契約未列固定字串清單。 | 聯絡電話。 |
| address1 | 選填 | string | 範例：`"456 Oak Ave"`<br>可輸入字串；契約未列固定字串清單。 | 地址資料。 |
| address2 | 選填 | string | 範例：`"Suite 100"`<br>可輸入字串；契約未列固定字串清單。 | 地址資料。 |
| city | 選填 | string | 範例：`"Los Angeles"`<br>可輸入字串；契約未列固定字串清單。 | 城市名稱。 |
| state | 選填 | string | 範例：`"CA"`<br>可輸入字串；契約未列固定字串清單。 | 參數 `state` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| postcode | 選填 | string | 範例：`"90001"`<br>可輸入字串；契約未列固定字串清單。 | 郵遞區號。 |
| country | 選填 | string | 範例：`"US"`<br>可輸入字串；契約未列固定字串清單。 | 國家或地區名稱。 |
| defaultAddress | 選填 | boolean | 範例：`false` | 是否設為預設地址。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Address updated」結果。 |
| 400 | 輸入資料無效。 |
| 404 | 找不到資源。 |
| 422 | 驗證錯誤。 |


<!-- MSDSS_API_EXTENSION_20261108 -->

---

以下為本次增補操作；原第 01–15 節內容保留不變。新增欄位沿用原表格，另補來源認證與巢狀結構；可輸入值列出來源的選項、預設、範例及限制。完整採用規則見 [增補計畫](../../api-extension/plan.md)。

## 16. 建立顧客帳號 API

`POST /customers`

**operationId：** api_apishopcustomers_post  
**來源檔案：** post-customers.json

**API 涵義：** 建立顧客帳號，供登入與會員購物流程使用。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 bearerAuth；同組其他方案亦須滿足。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例（非全部選項）：`""` | 前台 API 金鑰，用於驗證商店前台請求；所有 Shop／Storefront API 請求均須提供。 |
| header | X-Locale | 選填 | string | 範例（非全部選項）：`"en"` | 取得本地化資料的語系代碼，例如 en、fr、ar；預設使用銷售通路的預設語系。 |
| header | X-Channel | 選填 | string | 範例（非全部選項）：`"default"` | 銷售通路代碼，例如 default；預設使用目前通路。 |
| header | X-Currency | 選填 | string | 範例（非全部選項）：`"USD"` | 幣別代碼，例如 USD、EUR、INR；預設使用銷售通路的基準幣別。 |

### 請求本文

- 必填：否（來源未宣告本文必填；若送出本文，仍須符合欄位條件）
- Content-Type：`application/json`
- Schema 型別：`object`
- 本文格式／範例：範例（非全部選項）：`{"firstName": "John", "lastName": "Doe", "email": "john@example.com", "password": "Password123!", "confirmPassword": "Password123!"}`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| firstName | 必填 | string | 範例（非全部選項）：`"John"` | 顧客或收件人的名字。 |
| lastName | 必填 | string | 範例（非全部選項）：`"Doe"` | 顧客或收件人的姓氏。 |
| email | 必填 | string | 格式：`"email"`<br>範例（非全部選項）：`"john@example.com"` | 顧客電子郵件。 |
| password | 必填 | string | 格式：`"password"`<br>範例（非全部選項）：`"Password123!"` | 帳號密碼；實際值不進模型或一般日誌。 |
| confirmPassword | 必填 | string | 格式：`"password"`<br>範例（非全部選項）：`"Password123!"` | 再次輸入密碼以確認；須與 password 相符，實際值不進模型或一般日誌。 |
| phone | 選填 | string | 範例（非全部選項）：`"1234567890"` | 聯絡電話。 |
| gender | 選填 | string | 固定值：`Male`、`Female`、`Other` | 顧客性別，依規格列舉或實例設定填寫。 |
| dateOfBirth | 選填 | string | 格式：`"date"`<br>範例（非全部選項）：`"1990-01-15"` | 顧客出生日期。 |
| status | 選填 | integer | 範例（非全部選項）：`1` | 顧客狀態：1 表示啟用，0 表示停用。 |
| isVerified | 選填 | integer | 範例（非全部選項）：`1` | 顧客是否已驗證：1 表示已驗證，0 表示尚未驗證。 |
| isSuspended | 選填 | integer | 範例（非全部選項）：`0` | 顧客是否已停權：1 表示停權，0 表示正常啟用。 |
| subscribedToNewsLetter | 選填 | boolean | 布林可填值：`true`、`false`<br>範例（非全部選項）：`true` | 是否訂閱電子報。 |
| deviceToken | 選填 | string | 範例（非全部選項）：`"your-fcm-device-token"` | 裝置通知憑證；實際值不進模型或一般日誌。 |


**資料產生注意：** status、isVerified、isSuspended 是來源列出的顧客狀態欄位；不把任意設定驗證或停權狀態當成一般正常註冊流程，先核對實例權限與設定。

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 顧客註冊完成；回傳的 token 可供後續請求作為 Bearer 憑證。 |
| 422 | 驗證失敗，例如電子郵件已使用或兩次密碼不相符。 |
| 400 | 輸入資料無效。 |

## 17. 新增顧客地址 API

`POST /customer-addresses`

**operationId：** api_apishopcustomer-addresses_post  
**來源檔案：** post-customer-addresses.json

**API 涵義：** 新增顧客地址，供後續查詢與更新使用。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 bearerAuth；同組其他方案亦須滿足。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例（非全部選項）：`""` | 前台 API 金鑰，用於驗證商店前台請求；所有 Shop／Storefront API 請求均須提供。 |
| header | X-Locale | 選填 | string | 範例（非全部選項）：`"en"` | 取得本地化資料的語系代碼，例如 en、fr、ar；預設使用銷售通路的預設語系。 |
| header | X-Channel | 選填 | string | 範例（非全部選項）：`"default"` | 銷售通路代碼，例如 default；預設使用目前通路。 |
| header | X-Currency | 選填 | string | 範例（非全部選項）：`"USD"` | 幣別代碼，例如 USD、EUR、INR；預設使用銷售通路的基準幣別。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`
- 本文格式／範例：範例（非全部選項）：`{"company_name": "Acme Inc.", "first_name": "Api", "last_name": "Addr", "vat_id": "GB123456789", "address": "123 Main St", "city": "New York", "state": "NY", "country": "US", "postcode": "10001", "phone": "1234567890", "email": "api@example.com", "default_address": true}`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| firstName | 必填 | string | 範例（非全部選項）：`"John"` | 顧客或收件人的名字。 |
| lastName | 必填 | string | 範例（非全部選項）：`"Doe"` | 顧客或收件人的姓氏。 |
| companyName | 選填 | string | 範例（非全部選項）：`"Acme Inc."` | 公司名稱。 |
| vatId | 選填 | string | 範例（非全部選項）：`"GB123456789"` | 加值稅識別碼。 |
| email | 必填 | string | 格式：`"email"`<br>範例（非全部選項）：`"john@example.com"` | 顧客電子郵件。 |
| phone | 必填 | string | 範例（非全部選項）：`"1234567890"` | 聯絡電話。 |
| address1 | 必填 | string | 範例（非全部選項）：`"123 Main St"` | 地址第一行。 |
| address2 | 選填 | string | 範例（非全部選項）：`"Apt 4B"` | 地址第二行。 |
| city | 必填 | string | 範例（非全部選項）：`"New York"` | 城市。 |
| state | 必填 | string | 範例（非全部選項）：`"NY"` | 州／省。 |
| postcode | 必填 | string | 範例（非全部選項）：`"10001"` | 郵遞區號。 |
| country | 必填 | string | 範例（非全部選項）：`"US"` | 國家代碼或名稱，依此實例定義。 |
| defaultAddress | 選填 | boolean | 布林可填值：`true`、`false`<br>範例（非全部選項）：`true` | 是否設為預設地址。 |


### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 地址建立完成。 |
| 400 | 輸入資料無效。 |
| 422 | 資料驗證失敗。 |

## 18. 保存結帳配送方式 API

`POST /checkout-shipping-methods`

**operationId：** api_apishopcheckout-shipping-methods_post  
**來源檔案：** post-checkout-shipping-methods.json

**API 涵義：** 保存目前購物車選用的配送方式。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 bearerAuth；同組其他方案亦須滿足。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例（非全部選項）：`""` | 前台 API 金鑰，用於驗證商店前台請求；所有 Shop／Storefront API 請求均須提供。 |
| header | X-Locale | 選填 | string | 範例（非全部選項）：`"en"` | 取得本地化資料的語系代碼，例如 en、fr、ar；預設使用銷售通路的預設語系。 |
| header | X-Channel | 選填 | string | 範例（非全部選項）：`"default"` | 銷售通路代碼，例如 default；預設使用目前通路。 |
| header | X-Currency | 選填 | string | 範例（非全部選項）：`"USD"` | 幣別代碼，例如 USD、EUR、INR；預設使用銷售通路的基準幣別。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`
- 本文格式／範例：範例（非全部選項）：`{"shippingMethod": "flatrate_flatrate"}`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| shippingMethod | 必填 | string | 範例（非全部選項）：`"flatrate_flatrate"` | 選用的配送方式，取自目前購物車／配送紀錄的可用方式。 |


### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 配送方式已保存。 |
| 500 | 尚無購物車／結帳地址，或配送方式無效。 |
| 400 | 輸入資料無效。 |
| 422 | 資料驗證失敗。 |

## 19. 取得可用付款方式 API

`GET /payment-methods`

**operationId：** api_apishoppayment-methods_get_collection  
**來源檔案：** get-payment-methods.json

**API 涵義：** 取得目前購物車可使用的付款方式。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 bearerAuth；同組其他方案亦須滿足。 |
| query | page | 選填 | integer | 預設值：`1` | 資料集合的頁碼。 |
| query | per_page | 選填 | integer | 預設值：`10`<br>最小值：`0`<br>最大值：`50` | 每頁資料筆數。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例（非全部選項）：`""` | 前台 API 金鑰，用於驗證商店前台請求；所有 Shop／Storefront API 請求均須提供。 |
| header | X-Locale | 選填 | string | 範例（非全部選項）：`"en"` | 取得本地化資料的語系代碼，例如 en、fr、ar；預設使用銷售通路的預設語系。 |
| header | X-Channel | 選填 | string | 範例（非全部選項）：`"default"` | 銷售通路代碼，例如 default；預設使用目前通路。 |
| header | X-Currency | 選填 | string | 範例（非全部選項）：`"USD"` | 幣別代碼，例如 USD、EUR、INR；預設使用銷售通路的基準幣別。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 回傳可用付款方式。 |

## 20. 保存結帳付款方式 API

`POST /checkout-payment-methods`

**operationId：** api_apishopcheckout-payment-methods_post  
**來源檔案：** post-checkout-payment-methods.json

**API 涵義：** 保存目前購物車選用的付款方式。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 bearerAuth；同組其他方案亦須滿足。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例（非全部選項）：`""` | 前台 API 金鑰，用於驗證商店前台請求；所有 Shop／Storefront API 請求均須提供。 |
| header | X-Locale | 選填 | string | 範例（非全部選項）：`"en"` | 取得本地化資料的語系代碼，例如 en、fr、ar；預設使用銷售通路的預設語系。 |
| header | X-Channel | 選填 | string | 範例（非全部選項）：`"default"` | 銷售通路代碼，例如 default；預設使用目前通路。 |
| header | X-Currency | 選填 | string | 範例（非全部選項）：`"USD"` | 幣別代碼，例如 USD、EUR、INR；預設使用銷售通路的基準幣別。 |

### 請求本文

- 必填：是
- Content-Type：`application/json`
- Schema 型別：`object`
- 本文格式／範例：範例（非全部選項）：`{"paymentMethod": "moneytransfer"}`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| paymentMethod | 必填 | string | 範例（非全部選項）：`"moneytransfer"` | 選用的付款方式，取自目前購物車／付款紀錄的可用方式。 |
| paymentSuccessUrl | 選填 | string | 範例（非全部選項）：`"https://myapp.com/payment/success"` | 付款成功後導向的網址。 |
| paymentFailureUrl | 選填 | string | 範例（非全部選項）：`"https://myapp.com/payment/failure"` | 付款失敗後導向的網址。 |
| paymentCancelUrl | 選填 | string | 範例（非全部選項）：`"https://myapp.com/payment/cancel"` | 取消付款後導向的網址。 |


### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 付款方式已保存。 |
| 500 | 尚無購物車／配送設定，或付款方式無效。 |
| 400 | 輸入資料無效。 |
| 422 | 資料驗證失敗。 |

## 21. 建立訪客購物車憑證 API

`POST /cart-tokens`

**operationId：** createCartToken  
**來源檔案：** post-cart-tokens.json

**API 涵義：** 建立或取得訪客購物車的識別憑證，供後續購物車與結帳流程使用。

**採用角色：** 流程支援。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 bearerAuth；同組其他方案亦須滿足。 |
| header | X-STOREFRONT-KEY | 必填 | string | 範例（非全部選項）：`""` | 前台 API 金鑰，用於驗證商店前台請求；所有 Shop／Storefront API 請求均須提供。 |
| header | X-Locale | 選填 | string | 範例（非全部選項）：`"en"` | 取得本地化資料的語系代碼，例如 en、fr、ar；預設使用銷售通路的預設語系。 |
| header | X-Channel | 選填 | string | 範例（非全部選項）：`"default"` | 銷售通路代碼，例如 default；預設使用目前通路。 |
| header | X-Currency | 選填 | string | 範例（非全部選項）：`"USD"` | 幣別代碼，例如 USD、EUR、INR；預設使用銷售通路的基準幣別。 |

### 請求本文

- 必填：否（來源未宣告本文必填；若送出本文，仍須符合欄位條件）
- Content-Type：`application/json`
- Schema 型別：`object`
- 本文格式／範例：範例（非全部選項）：`{"guest_cart": {"createNew": true}, "guest_cart_with_session": {"sessionId": "my-session-id", "createNew": true}}`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| sessionId | 選填 | string | 範例（非全部選項）：`"my-session-id"` | 建立購物車使用的工作階段識別碼；選填。 |
| createNew | 選填 | boolean | 布林可填值：`true`、`false`<br>範例（非全部選項）：`true` | 是否產生具有獨立識別憑證的新購物車；選填。 |


### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 訪客購物車已建立；回傳識別憑證供後續購物車與結帳流程使用。 |
| 400 | 輸入資料無效。 |
| 422 | 資料驗證失敗。 |

### 既有 15 個操作的認證與契約補充

原第 01–15 節不改字，缺漏或受遮罩影響之處另列於此。下表只補認證方案，原參數表中的公開金鑰等要求仍適用；同一組的標頭同時滿足，不同組擇一。

| 既有操作 | 認證標頭／方式 | 來源 | 核對說明 |
|---|---|---|---|
| `GET /checkout-shipping-methods` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /customer-addresses` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /customer-orders` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /customer-profile` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /products/{id}` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /products` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /add-product-in-cart` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /cart` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /checkout-addresses` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /checkout-orders` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /customer/login` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /customer/logout` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /remove-cart-item` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /update-cart-item` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `PUT /customer-addresses/{id}` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |

16 份結構修正版的選用方式見 [既有 API 補充](../../api-extension/existing-api-supplements.md)，以新採用清單指向的檔案為準。

**登入欄位補充：** 原拆分檔的 password schema 受遮罩影響；修正版恢復原來源定義。

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| password | 送出登入本文時必填 | string | 格式：`"password"`<br>範例（非全部選項）：`"Password123!"` | 登入密碼；只恢復規格結構，實際值不進模型或一般日誌。 |

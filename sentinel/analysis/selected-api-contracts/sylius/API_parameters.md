# sylius API 契約參數

> 本文件直接依各 operation JSON 與來源 OpenAPI 重新整理。可輸入值只會列出契約已定義的 enum、預設值、範例與限制；未列固定值時，會明確說明資料型別。

## 01. 取得單一地址 API

`GET /api/v2/shop/addresses/{id}`

**operationId：** sylius_api_shop_address_get  
**來源檔案：** get-api-v2-shop-addresses-id.json

**API 涵義：** 回傳指定 Address 資源。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| path | id | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 資源的唯一識別碼。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | Address 資源。 |
| 403 | 禁止存取。 |
| 404 | 找不到資源。 |

## 02. 取得地址清單 API

`GET /api/v2/shop/addresses`

**operationId：** sylius_api_shop_address_get_collection  
**來源檔案：** get-api-v2-shop-addresses.json

**API 涵義：** 回傳 Address 資源集合。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| query | page | 選填 | integer | 預設值：`1` | 分頁頁碼。 |
| query | itemsPerPage | 選填 | integer | 預設值：`30`<br>最小值：0<br>最大值：30 | 每頁回傳的資料筆數。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | Address 資源集合。 |
| 403 | 禁止存取。 |

## 03. 取得訂單項目清單 API

`GET /api/v2/shop/orders/{tokenValue}/items`

**operationId：** sylius_api_shop_order_order_item_get_collection  
**來源檔案：** get-api-v2-shop-orders-tokenvalue-items.json

**API 涵義：** 回傳指定訂單的 OrderItem 資源集合。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| path | tokenValue | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 訂單流程的識別 token；屬敏感資料，不應寫入一般日誌。 |
| query | page | 選填 | integer | 預設值：`1` | 分頁頁碼。 |
| query | itemsPerPage | 選填 | integer | 預設值：`30`<br>最小值：0<br>最大值：30 | 每頁回傳的資料筆數。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「OrderItem collection」結果。 |

## 04. 取得單一訂單 API

`GET /api/v2/shop/orders/{tokenValue}`

**operationId：** sylius_api_shop_order_get  
**來源檔案：** get-api-v2-shop-orders-tokenvalue.json

**API 涵義：** 回傳指定訂單資源。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| path | tokenValue | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 訂單流程的識別 token；屬敏感資料，不應寫入一般日誌。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Order resource」結果。 |
| 404 | 找不到資源。 |

## 05. 取得訂單清單 API

`GET /api/v2/shop/orders`

**operationId：** sylius_api_shop_order_get_collection  
**來源檔案：** get-api-v2-shop-orders.json

**API 涵義：** 回傳 Order 資源集合。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| query | page | 選填 | integer | 預設值：`1` | 分頁頁碼。 |
| query | itemsPerPage | 選填 | integer | 預設值：`30`<br>最小值：0<br>最大值：30 | 每頁回傳的資料筆數。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Order collection」結果。 |
| 403 | 禁止存取。 |

## 06. 取得付款方式清單 API

`GET /api/v2/shop/payment-methods`

**operationId：** sylius_api_shop_payment_method_get_collection  
**來源檔案：** get-api-v2-shop-payment-methods.json

**API 涵義：** 回傳 PaymentMethod 資源集合。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | PaymentMethod 資源集合。 |

## 07. 依商品代碼取得商品 API

`GET /api/v2/shop/products/{code}`

**operationId：** sylius_api_shop_product_get  
**來源檔案：** get-api-v2-shop-products-code.json

**API 涵義：** 回傳指定 Product 資源。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| path | code | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 資源或商品代碼。 |
| query | imageFilter | 選填 | string | 固定值：`sylius_original`、`sylius_small`、`sylius_medium`、`sylius_large`、`sylius_admin_product_original`、`sylius_admin_avatar`、`sylius_admin_product_thumbnail`、`sylius_admin_product_large_thumbnail`、`sylius_shop_product_original`、`sylius_shop_product_small_thumbnail`、`sylius_shop_product_thumbnail`、`sylius_shop_product_large_thumbnail`、`sylius_shop_taxon_thumbnail` | 指定商品圖片使用的圖片處理樣式與尺寸。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | Product 資源。 |
| 404 | 找不到資源。 |

## 08. 取得商品清單 API

`GET /api/v2/shop/products`

**operationId：** sylius_api_shop_product_get_collection  
**來源檔案：** get-api-v2-shop-products.json

**API 涵義：** 回傳 Product 資源集合。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| query | page | 選填 | integer | 預設值：`1` | 分頁頁碼。 |
| query | itemsPerPage | 選填 | integer | 預設值：`30`<br>最小值：0<br>最大值：30 | 每頁回僵的資料筆數。 |
| query | translations.name | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 商品多語系名稱。 |
| query | productTaxons.taxon.code | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 用於篩選商品的分類代碼。 |
| query | productTaxons.taxon.code[] | 選填 | array | 可輸入 array值；契約未列出固定值。 | 用於篩選商品的分類代碼陣列。 |
| query | order[code] | 選填 | string | 固定值：`asc`、`desc`<br>預設值：`""` | 依訂單代碼排序。 |
| query | order[createdAt] | 選填 | string | 固定值：`asc`、`desc`<br>預設值：`""` | 依建立時間排序。 |
| query | order[price] | 選填 | string | 固定值：`asc`、`desc` | 依價格排序。 |
| query | order[translation.name] | 選填 | string | 固定值：`asc`、`desc` | 依多語系商品名稱排序。 |
| query | localeCode for order[translation.name] | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `localeCode for order[translation.name]` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | taxon | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 商品分類識別資料。 |
| query | association[typeCode] | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `association[typeCode]` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | association[ownerCode] | 選填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `association[ownerCode]` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| query | imageFilter | 選填 | string | 固定值：`sylius_original`、`sylius_small`、`sylius_medium`、`sylius_large`、`sylius_admin_product_original`、`sylius_admin_avatar`、`sylius_admin_product_thumbnail`、`sylius_admin_product_large_thumbnail`、`sylius_shop_product_original`、`sylius_shop_product_small_thumbnail`、`sylius_shop_product_thumbnail`、`sylius_shop_product_large_thumbnail`、`sylius_shop_taxon_thumbnail` | 指定商品圖片使用的圖片處理樣式與尺寸。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | Product 資源集合。 |

## 09. 更新訂單 API

`PATCH /api/v2/shop/orders/{tokenValue}/complete`

**operationId：** sylius_api_shop_order_patch_complete  
**來源檔案：** patch-api-v2-shop-orders-tokenvalue-complete.json

**API 涵義：** 回傳更新後的 Order 資源。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| path | tokenValue | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 訂單流程的識別 token；屬敏感資料，不應寫入一般日誌。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 請求本文

- 必填：是
- Content-Type：`application/merge-patch+json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| notes | 選填 | string,null | 可輸入 string,null值；契約未列出固定值。 | 備註。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Order resource updated」結果。 |
| 400 | 輸入資料無效。 |
| 404 | 找不到資源。 |
| 422 | 此狀態表示 API 回應了「An error occurred」結果。 |

## 10. 建立地址 API

`POST /api/v2/shop/addresses`

**operationId：** sylius_api_shop_address_post  
**來源檔案：** post-api-v2-shop-addresses.json

**API 涵義：** 回傳新建立的 Address 資源。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 請求本文

- 必填：是
- Content-Type：`application/ld+json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| firstName | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 名字。 |
| lastName | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 姓氏。 |
| phoneNumber | 選填 | string,null | 可輸入 string,null值；契約未列出固定值。 | 聯絡電話。 |
| company | 選填 | string,null | 可輸入 string,null值；契約未列出固定值。 | 公司名稱。 |
| countryCode | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 國家或地區代碼。 |
| provinceCode | 選填 | string,null | 可輸入 string,null值；契約未列出固定值。 | 省、州或地區代碼。 |
| provinceName | 選填 | string,null | 可輸入 string,null值；契約未列出固定值。 | 省、州或地區名稱。 |
| street | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `street` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| city | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 城市名稱。 |
| postcode | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 郵遞區號。 |
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| firstName | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 名字。 |
| lastName | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 姓氏。 |
| phoneNumber | 選填 | string,null | 可輸入 string,null值；契約未列出固定值。 | 聯絡電話。 |
| company | 選填 | string,null | 可輸入 string,null值；契約未列出固定值。 | 公司名稱。 |
| countryCode | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 國家或地區代碼。 |
| provinceCode | 選填 | string,null | 可輸入 string,null值；契約未列出固定值。 | 省、州或地區代碼。 |
| provinceName | 選填 | string,null | 可輸入 string,null值；契約未列出固定值。 | 省、州或地區名稱。 |
| street | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 參數 `street` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| city | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 城市名稱。 |
| postcode | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 郵遞區號。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 此狀態表示 API 回應了「Address resource created」結果。 |
| 400 | 輸入資料無效。 |
| 403 | 禁止存取。 |
| 422 | 此狀態表示 API 回應了「An error occurred」結果。 |

## 11. 顧客登入 API

`POST /api/v2/shop/customers/token`

**operationId：** postCustomerCredentialsItem  
**來源檔案：** post-api-v2-shop-customers-token.json

**API 涵義：** 回傳 JWT token，代表認證成功或失敗的結果。

**參數：** 此 operation 未列出 path、query、header 或 cookie 參數。

### 請求本文

- 必填：否
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| email | 選填 | string | 範例：`"shop@example.com"`<br>可輸入字串；契約未列固定字串清單。 | 顧客電子郵件地址。 |
| password | 選填 | string | 範例：`"sylius"`<br>可輸入字串；契約未列固定字串清單。 | 顧客密碼；屬敏感資料，不應寫入模型或一般日誌。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「JWT token retrieval succeeded」結果。 |
| 400 | 此狀態表示 API 回應了「JWT token retrieval failed due to invalid request」結果。 |
| 401 | 此狀態表示 API 回應了「JWT token retrieval failed due to invalid credentials」結果。 |

## 12. 建立顧客 API

`POST /api/v2/shop/customers`

**operationId：** sylius_api_shop_customer_post  
**來源檔案：** post-api-v2-shop-customers.json

**API 涵義：** 回傳新建立的 Customer 資源。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 請求本文

- 必填：是
- Content-Type：`application/ld+json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| firstName | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 名字。 |
| lastName | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 姓氏。 |
| email | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 顧客電子郵件地址。 |
| password | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 顧客密碼；屬敏感資料，不應寫入模型或一般日誌。 |
| subscribedToNewsletter | 選填 | boolean | 可輸入 boolean值；契約未列出固定值。 | 是否訂閱電子報。 |
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| firstName | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 名字。 |
| lastName | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 姓氏。 |
| email | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 顧客電子郵件地址。 |
| password | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 顧客密碼；屬敏感資料，不應寫入模型或一般日誌。 |
| subscribedToNewsletter | 選填 | boolean | 可輸入 boolean值；契約未列出固定值。 | 是否訂閱電子報。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 204 | Customer 資源已建立。 |
| 400 | 輸入資料無效。 |
| 422 | 此狀態表示 API 回應了「An error occurred」結果。 |

## 13. 建立訂單或新增訂單項目 API

`POST /api/v2/shop/orders/{tokenValue}/items`

**operationId：** sylius_api_shop_order_order_item_post  
**來源檔案：** post-api-v2-shop-orders-tokenvalue-items.json

**API 涵義：** 回傳建立或更新後的 Order 資源。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| path | tokenValue | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 訂單流程的識別 token；屬敏感資料，不應寫入一般日誌。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 請求本文

- 必填：是
- Content-Type：`application/ld+json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| productVariant | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 商品變體識別值。 |
| quantity | 必填 | integer | 最小值：1 | 要加入或更新的商品數量。 |
- Content-Type：`application/json`
- Schema 型別：`object`

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| productVariant | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 商品變體識別值。 |
| quantity | 必填 | integer | 最小值：1 | 要加入或更新的商品數量。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | Order 資源已建立。 |
| 400 | 輸入資料無效。 |
| 422 | 此狀態表示 API 回應了「An error occurred」結果。 |


<!-- MSDSS_API_EXTENSION_20261108 -->

---

以下為本次增補操作；原第 01–15 節內容保留不變。新增欄位沿用原表格，另補來源認證與巢狀結構；可輸入值列出來源的選項、預設、範例及限制。完整採用規則見 [增補計畫](../../api-extension/plan.md)。

## 14. 建立購物車 API

`POST /api/v2/shop/orders`

**operationId：** sylius_api_shop_order_post  
**來源檔案：** post-api-v2-shop-orders.json

**API 涵義：** 建立購物車／訂單並取得 tokenValue。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 JWT；同組其他方案亦須滿足。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 列舉包含商店定義的全部語系；實際上只有目前通路已啟用的語系可使用。 |

### 請求本文

- 必填：是
- Content-Type：`application/ld+json`
- Schema 型別：`object`
- 本文格式／範例：可輸入物件；具名子欄位見下表，契約未列固定選項。

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| （本文） | 依來源契約 | object | 來源沒有明列具名欄位；不能推定任意本文都有效 | 此操作宣告接收物件，實際所需狀態與額外條件須在固定實例核對。 |

- Content-Type：`application/json`
- Schema 型別：`object`
- 本文格式／範例：可輸入物件；具名子欄位見下表，契約未列固定選項。

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| （本文） | 依來源契約 | object | 來源沒有明列具名欄位；不能推定任意本文都有效 | 此操作宣告接收物件，實際所需狀態與額外條件須在固定實例核對。 |


### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 201 | 購物車／訂單資料已建立。 |
| 400 | 輸入資料無效。 |
| 422 | 處理時發生錯誤。 |

## 15. 更新購物車地址與聯絡資料 API

`PUT /api/v2/shop/orders/{tokenValue}`

**operationId：** sylius_api_shop_order_put  
**來源檔案：** put-api-v2-shop-orders-tokenvalue.json

**API 涵義：** 設定購物車的 email、帳單地址、配送地址或優惠碼。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 JWT；同組其他方案亦須滿足。 |
| path | tokenValue | 必填 | string | — | 訂單的識別值；此路徑以 tokenValue 識別購物車／訂單。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 列舉包含商店定義的全部語系；實際上只有目前通路已啟用的語系可使用。 |

### 請求本文

- 必填：是
- Content-Type：`application/ld+json`
- Schema 型別：`object`
- 本文格式／範例：可輸入物件；具名子欄位見下表，契約未列固定選項。

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| email | 選填 | string／null | 格式：`"email"`<br>最多字元數：`254`<br>可填 `null` | 顧客電子郵件。 |
| billingAddress | 選填 | 依契約 | 至少符合一種結構第 1 組：可輸入物件；具名子欄位見下表，契約未列固定選項。<br>至少符合一種結構第 2 組：可填 `null` | 帳單地址物件。 |
| billingAddress〈anyOf分支2〉 | 元素／分支格式 | null | 可填 `null` | 帳單地址物件。 |
| shippingAddress | 選填 | 依契約 | 至少符合一種結構第 1 組：可輸入物件；具名子欄位見下表，契約未列固定選項。<br>至少符合一種結構第 2 組：可填 `null` | 配送地址物件。 |
| shippingAddress〈anyOf分支2〉 | 元素／分支格式 | null | 可填 `null` | 配送地址物件。 |
| couponCode | 選填 | string／null | 可填 `null` | 套用的優惠券代碼。 |

- Content-Type：`application/json`
- Schema 型別：`object`
- 本文格式／範例：可輸入物件；具名子欄位見下表，契約未列固定選項。

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| email | 選填 | string／null | 格式：`"email"`<br>最多字元數：`254`<br>可填 `null` | 顧客電子郵件。 |
| billingAddress | 選填 | 依契約 | 至少符合一種結構第 1 組：可輸入物件；具名子欄位見下表，契約未列固定選項。<br>至少符合一種結構第 2 組：可填 `null` | 帳單地址物件。 |
| billingAddress〈anyOf分支2〉 | 元素／分支格式 | null | 可填 `null` | 帳單地址物件。 |
| shippingAddress | 選填 | 依契約 | 至少符合一種結構第 1 組：可輸入物件；具名子欄位見下表，契約未列固定選項。<br>至少符合一種結構第 2 組：可填 `null` | 配送地址物件。 |
| shippingAddress〈anyOf分支2〉 | 元素／分支格式 | null | 可填 `null` | 配送地址物件。 |
| couponCode | 選填 | string／null | 可填 `null` | 套用的優惠券代碼。 |


### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 訂單資料已更新。 |
| 400 | 輸入資料無效。 |
| 422 | 處理時發生錯誤。 |
| 404 | 找不到指定資源。 |

## 16. 更新購物車品項數量 API

`PATCH /api/v2/shop/orders/{tokenValue}/items/{orderItemId}`

**operationId：** sylius_api_shop_order_order_item_patch  
**來源檔案：** patch-api-v2-shop-orders-tokenvalue-items-orderitemid.json

**API 涵義：** 更新指定購物車品項的數量。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 JWT；同組其他方案亦須滿足。 |
| path | tokenValue | 必填 | string | — | 訂單的識別值；此路徑以 tokenValue 識別購物車／訂單。 |
| path | orderItemId | 必填 | string | — | 訂單品項的識別碼。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 列舉包含商店定義的全部語系；實際上只有目前通路已啟用的語系可使用。 |

### 請求本文

- 必填：是
- Content-Type：`application/merge-patch+json`
- Schema 型別：`object`
- 本文格式／範例：可輸入物件；具名子欄位見下表，契約未列固定選項。

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| quantity | 選填 | integer | 最小值：`1` | 品項購買數量。 |


### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 訂單資料已更新。 |
| 400 | 輸入資料無效。 |
| 422 | 處理時發生錯誤。 |
| 404 | 找不到指定資源。 |

## 17. 移除購物車品項 API

`DELETE /api/v2/shop/orders/{tokenValue}/items/{orderItemId}`

**operationId：** sylius_api_shop_order_order_item_delete  
**來源檔案：** delete-api-v2-shop-orders-tokenvalue-items-orderitemid.json

**API 涵義：** 移除指定購物車品項。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 JWT；同組其他方案亦須滿足。 |
| path | tokenValue | 必填 | string | — | 訂單的識別值；此路徑以 tokenValue 識別購物車／訂單。 |
| path | orderItemId | 必填 | string | — | 訂單品項的識別碼。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 列舉包含商店定義的全部語系；實際上只有目前通路已啟用的語系可使用。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 204 | 來源將此回應描述為訂單資料已刪除；本操作用於移除指定訂單品項。 |
| 404 | 找不到指定資源。 |

## 18. 設定訂單配送方式 API

`PATCH /api/v2/shop/orders/{tokenValue}/shipments/{shipmentId}`

**operationId：** sylius_api_shop_order_shipment_patch  
**來源檔案：** patch-api-v2-shop-orders-tokenvalue-shipments-shipmentid.json

**API 涵義：** 設定該配送紀錄選用的配送方式。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 JWT；同組其他方案亦須滿足。 |
| path | tokenValue | 必填 | string | — | 訂單的識別值；此路徑以 tokenValue 識別購物車／訂單。 |
| path | shipmentId | 必填 | string | — | 配送紀錄的識別碼。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 列舉包含商店定義的全部語系；實際上只有目前通路已啟用的語系可使用。 |

### 請求本文

- 必填：是
- Content-Type：`application/merge-patch+json`
- Schema 型別：`object`
- 本文格式／範例：可輸入物件；具名子欄位見下表，契約未列固定選項。

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| shippingMethod | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 選用的配送方式，取自目前購物車／配送紀錄的可用方式。 |


**識別值格式：** 欄位需依實例接受的資源參照填寫，可能使用 IRI（資源路徑）；從對應 /methods 回應取得，不自行把它改成其他平台的裸 ID。

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 訂單資料已更新。 |
| 400 | 輸入資料無效。 |
| 422 | 處理時發生錯誤。 |
| 404 | 找不到指定資源。 |

## 19. 設定訂單付款方式 API

`PATCH /api/v2/shop/orders/{tokenValue}/payments/{paymentId}`

**operationId：** sylius_api_shop_order_payment_patch  
**來源檔案：** patch-api-v2-shop-orders-tokenvalue-payments-paymentid.json

**API 涵義：** 設定該付款紀錄選用的付款方式。

**採用角色：** 核心。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 JWT；同組其他方案亦須滿足。 |
| path | tokenValue | 必填 | string | — | 訂單的識別值；此路徑以 tokenValue 識別購物車／訂單。 |
| path | paymentId | 必填 | string | — | 付款紀錄的識別碼。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 列舉包含商店定義的全部語系；實際上只有目前通路已啟用的語系可使用。 |

### 請求本文

- 必填：是
- Content-Type：`application/merge-patch+json`
- Schema 型別：`object`
- 本文格式／範例：可輸入物件；具名子欄位見下表，契約未列固定選項。

| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|
| paymentMethod | 選填 | string | 可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。 | 選用的付款方式，取自目前購物車／付款紀錄的可用方式。 |


**識別值格式：** 欄位需依實例接受的資源參照填寫，可能使用 IRI（資源路徑）；從對應 /methods 回應取得，不自行把它改成其他平台的裸 ID。

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 訂單資料已更新。 |
| 400 | 輸入資料無效。 |
| 422 | 處理時發生錯誤。 |
| 404 | 找不到指定資源。 |

## 20. 查詢此配送紀錄的可用方式 API

`GET /api/v2/shop/orders/{tokenValue}/shipments/{shipmentId}/methods`

**operationId：** sylius_api_shop_order_shipment_shipping_method_get_collection  
**來源檔案：** get-api-v2-shop-orders-tokenvalue-shipments-shipmentid-methods.json

**API 涵義：** 查詢該配送紀錄可選的配送方式。

**採用角色：** 流程支援。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 JWT；同組其他方案亦須滿足。 |
| path | tokenValue | 必填 | string | — | 訂單的識別值；此路徑以 tokenValue 識別購物車／訂單。 |
| path | shipmentId | 必填 | string | — | 配送紀錄的識別碼。 |
| query | page | 選填 | integer | 預設值：`1` | 資料集合的頁碼。 |
| query | itemsPerPage | 選填 | integer | 預設值：`30`<br>最小值：`0`<br>最大值：`30` | 每頁資料筆數。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 列舉包含商店定義的全部語系；實際上只有目前通路已啟用的語系可使用。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 回傳此配送紀錄可用的配送方式清單。 |

## 21. 查詢此付款紀錄的可用方式 API

`GET /api/v2/shop/orders/{tokenValue}/payments/{paymentId}/methods`

**operationId：** sylius_api_shop_order_payment_payment_method_get_collection  
**來源檔案：** get-api-v2-shop-orders-tokenvalue-payments-paymentid-methods.json

**API 涵義：** 查詢該付款紀錄可選的付款方式。

**採用角色：** 流程支援。

**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | Authorization | 採第 1 組認證時必填 | string | 格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集 | 來源認證方案 JWT；同組其他方案亦須滿足。 |
| path | tokenValue | 必填 | string | — | 訂單的識別值；此路徑以 tokenValue 識別購物車／訂單。 |
| path | paymentId | 必填 | string | — | 付款紀錄的識別碼。 |
| query | page | 選填 | integer | 預設值：`1` | 資料集合的頁碼。 |
| query | itemsPerPage | 選填 | integer | 預設值：`30`<br>最小值：`0`<br>最大值：`30` | 每頁資料筆數。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 列舉包含商店定義的全部語系；實際上只有目前通路已啟用的語系可使用。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 回傳此付款紀錄可用的付款方式清單。 |

### 既有 15 個操作的認證與契約補充

原第 01–15 節不改字，缺漏或受遮罩影響之處另列於此。下表只補認證方案，原參數表中的公開金鑰等要求仍適用；同一組的標頭同時滿足，不同組擇一。

| 既有操作 | 認證標頭／方式 | 來源 | 核對說明 |
|---|---|---|---|
| `GET /api/v2/shop/addresses/{id}` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /api/v2/shop/addresses` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /api/v2/shop/orders/{tokenValue}/items` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /api/v2/shop/orders/{tokenValue}` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /api/v2/shop/orders` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /api/v2/shop/payment-methods` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /api/v2/shop/products-by-slug/{slug}` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /api/v2/shop/products/{code}` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `GET /api/v2/shop/products` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `PATCH /api/v2/shop/orders/{tokenValue}/complete` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /api/v2/shop/addresses` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /api/v2/shop/customers/token` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /api/v2/shop/customers` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |
| `POST /api/v2/shop/orders/{tokenValue}/items` | `Authorization`（Bearer 憑證） | 繼承來源根層 | 依來源宣告，實際訪客與會員權限仍須核對。 |

16 份結構修正版的選用方式見 [既有 API 補充](../../api-extension/existing-api-supplements.md)，以新採用清單指向的檔案為準。

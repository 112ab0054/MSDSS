## 07. 依網址識別字串取得商品 API

`GET /api/v2/shop/products-by-slug/{slug}`

**operationId：** sylius_api_shop_product_get_by_slug
**來源檔案：** get-api-v2-shop-products-by-slug-slug.json

**API 涵義：** 回傳指定 Product 資源。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| path | slug | 必填 | string | 可輸入字串；契約未列固定字串清單。 | 商品網址識別字串。 |
| query | imageFilter | 選填 | string | 固定值：`sylius_original`、`sylius_small`、`sylius_medium`、`sylius_large`、`sylius_admin_product_original`、`sylius_admin_avatar`、`sylius_admin_product_thumbnail`、`sylius_admin_product_large_thumbnail`、`sylius_shop_product_original`、`sylius_shop_product_small_thumbnail`、`sylius_shop_product_thumbnail`、`sylius_shop_product_large_thumbnail`、`sylius_shop_taxon_thumbnail` | 指定商品圖片使用的圖片處理樣式與尺寸。 |
| header | Accept-Language | 選填 | string | 固定值：`en_US`、`de_DE`、`fr_FR`、`pl_PL`、`es_ES`、`es_MX`、`pt_PT`、`zh_CN`、`fr_GQ` | 要求回應使用的語系。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | Product 資源。 |
| 404 | 找不到資源。 |

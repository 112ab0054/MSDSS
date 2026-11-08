# sylius API 索引

共 22 個操作。[API 用途與填寫參數](API_parameters.md)。

下表連到實際採用的契約，包含另外保存的修正版；不要以舊目錄檔案是否存在判斷採用優先順序。

| Method | Path | 角色 | 採用契約 |
|---|---|---|---|
| GET | `/api/v2/shop/addresses/{id}` | 核心 | [JSON](get-api-v2-shop-addresses-id.json) |
| GET | `/api/v2/shop/addresses` | 核心 | [JSON](get-api-v2-shop-addresses.json) |
| GET | `/api/v2/shop/orders/{tokenValue}/items` | 核心 | [JSON](get-api-v2-shop-orders-tokenvalue-items.json) |
| GET | `/api/v2/shop/orders/{tokenValue}` | 核心 | [JSON](get-api-v2-shop-orders-tokenvalue.json) |
| GET | `/api/v2/shop/orders` | 核心 | [JSON](get-api-v2-shop-orders.json) |
| GET | `/api/v2/shop/payment-methods` | 核心 | [JSON](get-api-v2-shop-payment-methods.json) |
| GET | `/api/v2/shop/products-by-slug/{slug}` | 核心 | [JSON](get-api-v2-shop-products-by-slug-slug.json) |
| GET | `/api/v2/shop/products/{code}` | 核心 | [JSON](get-api-v2-shop-products-code.json) |
| GET | `/api/v2/shop/products` | 核心 | [JSON](get-api-v2-shop-products.json) |
| PATCH | `/api/v2/shop/orders/{tokenValue}/complete` | 核心 | [JSON](patch-api-v2-shop-orders-tokenvalue-complete.json) |
| POST | `/api/v2/shop/addresses` | 核心 | [JSON](post-api-v2-shop-addresses.json) |
| POST | `/api/v2/shop/customers/token` | 核心 | [JSON](post-api-v2-shop-customers-token.json) |
| POST | `/api/v2/shop/customers` | 核心 | [JSON](post-api-v2-shop-customers.json) |
| POST | `/api/v2/shop/orders/{tokenValue}/items` | 核心 | [JSON](post-api-v2-shop-orders-tokenvalue-items.json) |
| POST | `/api/v2/shop/orders` | 核心 | [JSON](post-api-v2-shop-orders.json) |
| PUT | `/api/v2/shop/orders/{tokenValue}` | 核心 | [JSON](put-api-v2-shop-orders-tokenvalue.json) |
| PATCH | `/api/v2/shop/orders/{tokenValue}/items/{orderItemId}` | 核心 | [JSON](patch-api-v2-shop-orders-tokenvalue-items-orderitemid.json) |
| DELETE | `/api/v2/shop/orders/{tokenValue}/items/{orderItemId}` | 核心 | [JSON](delete-api-v2-shop-orders-tokenvalue-items-orderitemid.json) |
| PATCH | `/api/v2/shop/orders/{tokenValue}/shipments/{shipmentId}` | 核心 | [JSON](patch-api-v2-shop-orders-tokenvalue-shipments-shipmentid.json) |
| PATCH | `/api/v2/shop/orders/{tokenValue}/payments/{paymentId}` | 核心 | [JSON](patch-api-v2-shop-orders-tokenvalue-payments-paymentid.json) |
| GET | `/api/v2/shop/orders/{tokenValue}/shipments/{shipmentId}/methods` | 流程支援 | [JSON](get-api-v2-shop-orders-tokenvalue-shipments-shipmentid-methods.json) |
| GET | `/api/v2/shop/orders/{tokenValue}/payments/{paymentId}/methods` | 流程支援 | [JSON](get-api-v2-shop-orders-tokenvalue-payments-paymentid-methods.json) |

來源：`sentinel/analysis/api-contracts/sylius/openapi-demo.json`；規格版本：`0.0.0`。固定部署版本與正常流程尚未完成核對。

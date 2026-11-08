# bagisto API 索引

共 21 個操作。[API 用途與填寫參數](API_parameters.md)。

下表連到實際採用的契約，包含另外保存的修正版；不要以舊目錄檔案是否存在判斷採用優先順序。

| Method | Path | 角色 | 採用契約 |
|---|---|---|---|
| GET | `/checkout-shipping-methods` | 核心 | [JSON](get-checkout-shipping-methods.json) |
| GET | `/customer-addresses` | 核心 | [JSON](get-customer-addresses.json) |
| GET | `/customer-orders` | 核心 | [JSON](get-customer-orders.json) |
| GET | `/customer-profile` | 核心 | [JSON](get-customer-profile.json) |
| GET | `/products/{id}` | 核心 | [JSON](get-products-id.json) |
| GET | `/products` | 核心 | [JSON](get-products.json) |
| POST | `/add-product-in-cart` | 核心 | [JSON](post-add-product-in-cart.json) |
| POST | `/cart` | 核心 | [JSON](post-cart.json) |
| POST | `/checkout-addresses` | 核心 | [JSON](post-checkout-addresses.json) |
| POST | `/checkout-orders` | 核心 | [JSON](post-checkout-orders.json) |
| POST | `/customer/login` | 核心 | [JSON](../../api-extension/contract-corrections/bagisto/post-customer-login.json) |
| POST | `/customer/logout` | 核心 | [JSON](post-customer-logout.json) |
| POST | `/remove-cart-item` | 核心 | [JSON](post-remove-cart-item.json) |
| POST | `/update-cart-item` | 核心 | [JSON](post-update-cart-item.json) |
| PUT | `/customer-addresses/{id}` | 核心 | [JSON](put-customer-addresses-id.json) |
| POST | `/customers` | 核心 | [JSON](post-customers.json) |
| POST | `/customer-addresses` | 核心 | [JSON](post-customer-addresses.json) |
| POST | `/checkout-shipping-methods` | 核心 | [JSON](post-checkout-shipping-methods.json) |
| GET | `/payment-methods` | 核心 | [JSON](get-payment-methods.json) |
| POST | `/checkout-payment-methods` | 核心 | [JSON](post-checkout-payment-methods.json) |
| POST | `/cart-tokens` | 流程支援 | [JSON](post-cart-tokens.json) |

來源：`sentinel/analysis/api-contracts/bagisto/openapi-shop.json`；規格版本：`2.4.10`。固定部署版本與正常流程尚未完成核對。

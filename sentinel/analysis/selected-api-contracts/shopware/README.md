# shopware API 索引

共 21 個操作。[API 用途與填寫參數](API_parameters.md)。

下表連到實際採用的契約，包含另外保存的修正版；不要以舊目錄檔案是否存在判斷採用優先順序。

| Method | Path | 角色 | 採用契約 |
|---|---|---|---|
| GET | `/checkout/cart` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/get-checkout-cart.json) |
| GET | `/checkout/gateway` | 選用 | [JSON](../../api-extension/contract-corrections/shopware/get-checkout-gateway.json) |
| POST | `/account/address` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-account-address.json) |
| POST | `/account/customer` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-account-customer.json) |
| POST | `/account/list-address` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-account-list-address.json) |
| POST | `/account/login` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-account-login.json) |
| POST | `/account/logout` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-account-logout.json) |
| POST | `/account/register` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-account-register.json) |
| POST | `/checkout/cart/line-item/delete` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-checkout-cart-line-item-delete.json) |
| POST | `/checkout/cart/line-item` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-checkout-cart-line-item.json) |
| POST | `/checkout/order` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-checkout-order.json) |
| POST | `/product-listing/{categoryId}` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-product-listing-categoryid.json) |
| POST | `/product/{productId}` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-product-productid.json) |
| POST | `/product` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-product.json) |
| POST | `/search` | 核心 | [JSON](../../api-extension/contract-corrections/shopware/post-search.json) |
| PATCH | `/checkout/cart/line-item` | 核心 | [JSON](patch-checkout-cart-line-item.json) |
| PATCH | `/context` | 核心 | [JSON](patch-context.json) |
| POST | `/order` | 核心 | [JSON](post-order.json) |
| GET | `/context` | 流程支援 | [JSON](get-context.json) |
| GET | `/payment-method` | 流程支援 | [JSON](get-payment-method.json) |
| GET | `/shipping-method` | 流程支援 | [JSON](get-shipping-method.json) |

來源：`sentinel/analysis/api-contracts/shopware/storeapi.json`；規格版本：`6.7.9999999-dev`。固定部署版本與正常流程尚未完成核對。

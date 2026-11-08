# 既有 API 的補充核對

此文件補充既有 45 操作的契約與流程問題，不覆寫原標題、參數表格或 JSON。

## 修正版契約的選用

遮罩造成結構差異的 16 份 JSON 另存 contract-corrections；active-api-manifest.json 指向修正版。其餘既有操作仍指向原檔，解析參照與繼承認證時使用記錄的來源規格。消費清單時不得只掃舊目錄而忽略修正版路徑。

修正版是包含相依元件的操作片段，不是獨立完整 OpenAPI 文件；原始範例值省略，schema、列舉、預設值與認證 scopes 的結構保留。

| 平台 | 操作 | 原檔 | 修正版 |
|---|---|---|---|
| bagisto | `POST /customer/login` | `sentinel/analysis/selected-api-contracts/bagisto/post-customer-login.json` | [post-customer-login.json](contract-corrections/bagisto/post-customer-login.json) |
| shopware | `GET /checkout/cart` | `sentinel/analysis/selected-api-contracts/shopware/get-checkout-cart.json` | [get-checkout-cart.json](contract-corrections/shopware/get-checkout-cart.json) |
| shopware | `GET /checkout/gateway` | `sentinel/analysis/selected-api-contracts/shopware/get-checkout-gateway.json` | [get-checkout-gateway.json](contract-corrections/shopware/get-checkout-gateway.json) |
| shopware | `POST /account/address` | `sentinel/analysis/selected-api-contracts/shopware/post-account-address.json` | [post-account-address.json](contract-corrections/shopware/post-account-address.json) |
| shopware | `POST /account/customer` | `sentinel/analysis/selected-api-contracts/shopware/post-account-customer.json` | [post-account-customer.json](contract-corrections/shopware/post-account-customer.json) |
| shopware | `POST /account/list-address` | `sentinel/analysis/selected-api-contracts/shopware/post-account-list-address.json` | [post-account-list-address.json](contract-corrections/shopware/post-account-list-address.json) |
| shopware | `POST /account/login` | `sentinel/analysis/selected-api-contracts/shopware/post-account-login.json` | [post-account-login.json](contract-corrections/shopware/post-account-login.json) |
| shopware | `POST /account/logout` | `sentinel/analysis/selected-api-contracts/shopware/post-account-logout.json` | [post-account-logout.json](contract-corrections/shopware/post-account-logout.json) |
| shopware | `POST /account/register` | `sentinel/analysis/selected-api-contracts/shopware/post-account-register.json` | [post-account-register.json](contract-corrections/shopware/post-account-register.json) |
| shopware | `POST /checkout/cart/line-item/delete` | `sentinel/analysis/selected-api-contracts/shopware/post-checkout-cart-line-item-delete.json` | [post-checkout-cart-line-item-delete.json](contract-corrections/shopware/post-checkout-cart-line-item-delete.json) |
| shopware | `POST /checkout/cart/line-item` | `sentinel/analysis/selected-api-contracts/shopware/post-checkout-cart-line-item.json` | [post-checkout-cart-line-item.json](contract-corrections/shopware/post-checkout-cart-line-item.json) |
| shopware | `POST /checkout/order` | `sentinel/analysis/selected-api-contracts/shopware/post-checkout-order.json` | [post-checkout-order.json](contract-corrections/shopware/post-checkout-order.json) |
| shopware | `POST /product-listing/{categoryId}` | `sentinel/analysis/selected-api-contracts/shopware/post-product-listing-categoryid.json` | [post-product-listing-categoryid.json](contract-corrections/shopware/post-product-listing-categoryid.json) |
| shopware | `POST /product/{productId}` | `sentinel/analysis/selected-api-contracts/shopware/post-product-productid.json` | [post-product-productid.json](contract-corrections/shopware/post-product-productid.json) |
| shopware | `POST /product` | `sentinel/analysis/selected-api-contracts/shopware/post-product.json` | [post-product.json](contract-corrections/shopware/post-product.json) |
| shopware | `POST /search` | `sentinel/analysis/selected-api-contracts/shopware/post-search.json` | [post-search.json](contract-corrections/shopware/post-search.json) |

## 認證與流程補充

- 所有操作的 effective_security 都保存在新採用清單；缺少 operation.security 時繼承來源根層，明列空陣列才取消繼承。 scopes 必須是陣列。
- Bagisto 登入 password 應保留為字串型別的 schema 物件，不能把整個 schema 遮成文字；來源部分 properties=[] 為上游結構問題，需實例核對，不自行猜欄位。
- Shopware 的 ApiKey 與 ContextToken 是認證方案，不能遮掉 scopes 結構；sw-context-source=session 與 sw-context-token 互斥，不可照範例同時送出。
- Bagisto POST /cart 用於讀取／重算目前購物車；訪客另用 /cart-tokens。POST /checkout-orders 回傳 redirect=true 不代表訂單與付款已完成。
- Shopware POST /checkout/order 建單、POST /order 查單；GET /checkout/gateway 不能取代 PATCH /context 保存設定。
- Sylius 使用 order token 表示購物車；配送與付款可能採 IRI，PATCH 保留 application/merge-patch+json。

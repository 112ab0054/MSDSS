# 現行訓練 API 索引

更新日期：2026-11-08。共 64 個操作：Bagisto 21、Shopware 21、Sylius 22。第一版 normal、sqli、xss。

本索引依 [採用清單](api-extension/active-api-manifest.json) 整理；API 標題取自現有參數文件，不重寫參數表格。原先 45 操作清單與審查已歸檔，不能當成目前完整範圍。

角色：核心用於共同業務研究；流程支援用於建立狀態並保留正常流量；選用功能不阻擋第一版購物流程。所有操作仍待固定實例實測。

## bagisto：21 個操作

[用途與填寫參數](selected-api-contracts/bagisto/API_parameters.md)

| 角色 | Method | Path | 中文標題 | 採用契約 |
|---|---|---|---|---|
| 核心 | GET | `/checkout-shipping-methods` | 取得購物車配送方式 API | [JSON](selected-api-contracts/bagisto/get-checkout-shipping-methods.json) |
| 核心 | GET | `/customer-addresses` | 取得顧客地址清單 API | [JSON](selected-api-contracts/bagisto/get-customer-addresses.json) |
| 核心 | GET | `/customer-orders` | 取得顧客訂單清單 API | [JSON](selected-api-contracts/bagisto/get-customer-orders.json) |
| 核心 | GET | `/customer-profile` | 取得顧客個人資料 API | [JSON](selected-api-contracts/bagisto/get-customer-profile.json) |
| 核心 | GET | `/products/{id}` | 取得單一商品及關聯資料 API | [JSON](selected-api-contracts/bagisto/get-products-id.json) |
| 核心 | GET | `/products` | 搜尋及篩選商品 API | [JSON](selected-api-contracts/bagisto/get-products.json) |
| 核心 | POST | `/add-product-in-cart` | 新增商品至購物車 API | [JSON](selected-api-contracts/bagisto/post-add-product-in-cart.json) |
| 核心 | POST | `/cart` | 取得目前購物車 API | [JSON](selected-api-contracts/bagisto/post-cart.json) |
| 核心 | POST | `/checkout-addresses` | 儲存購物車地址 API | [JSON](selected-api-contracts/bagisto/post-checkout-addresses.json) |
| 核心 | POST | `/checkout-orders` | 完成結帳並建立訂單 API | [JSON](selected-api-contracts/bagisto/post-checkout-orders.json) |
| 核心 | POST | `/customer/login` | 顧客登入 API | [JSON](api-extension/contract-corrections/bagisto/post-customer-login.json) |
| 核心 | POST | `/customer/logout` | 顧客登出 API | [JSON](selected-api-contracts/bagisto/post-customer-logout.json) |
| 核心 | POST | `/remove-cart-item` | 移除購物車商品 API | [JSON](selected-api-contracts/bagisto/post-remove-cart-item.json) |
| 核心 | POST | `/update-cart-item` | 更新購物車商品數量 API | [JSON](selected-api-contracts/bagisto/post-update-cart-item.json) |
| 核心 | PUT | `/customer-addresses/{id}` | 更新顧客地址 API | [JSON](selected-api-contracts/bagisto/put-customer-addresses-id.json) |
| 核心 | POST | `/customers` | 建立顧客帳號 API | [JSON](selected-api-contracts/bagisto/post-customers.json) |
| 核心 | POST | `/customer-addresses` | 新增顧客地址 API | [JSON](selected-api-contracts/bagisto/post-customer-addresses.json) |
| 核心 | POST | `/checkout-shipping-methods` | 保存結帳配送方式 API | [JSON](selected-api-contracts/bagisto/post-checkout-shipping-methods.json) |
| 核心 | GET | `/payment-methods` | 取得可用付款方式 API | [JSON](selected-api-contracts/bagisto/get-payment-methods.json) |
| 核心 | POST | `/checkout-payment-methods` | 保存結帳付款方式 API | [JSON](selected-api-contracts/bagisto/post-checkout-payment-methods.json) |
| 流程支援 | POST | `/cart-tokens` | 建立訪客購物車憑證 API | [JSON](selected-api-contracts/bagisto/post-cart-tokens.json) |

## shopware：21 個操作

[用途與填寫參數](selected-api-contracts/shopware/API_parameters.md)

| 角色 | Method | Path | 中文標題 | 採用契約 |
|---|---|---|---|---|
| 核心 | GET | `/checkout/cart` | 取得購物車 API | [JSON](api-extension/contract-corrections/shopware/get-checkout-cart.json) |
| 選用 | GET | `/checkout/gateway` | 呼叫結帳關卡 API | [JSON](api-extension/contract-corrections/shopware/get-checkout-gateway.json) |
| 核心 | POST | `/account/address` | 建立顧客地址 API | [JSON](api-extension/contract-corrections/shopware/post-account-address.json) |
| 核心 | POST | `/account/customer` | 取得顧客資料 API | [JSON](api-extension/contract-corrections/shopware/post-account-customer.json) |
| 核心 | POST | `/account/list-address` | 查詢顧客地址 API | [JSON](api-extension/contract-corrections/shopware/post-account-list-address.json) |
| 核心 | POST | `/account/login` | 顧客登入 API | [JSON](api-extension/contract-corrections/shopware/post-account-login.json) |
| 核心 | POST | `/account/logout` | 顧客登出 API | [JSON](api-extension/contract-corrections/shopware/post-account-logout.json) |
| 核心 | POST | `/account/register` | 註冊顧客 API | [JSON](api-extension/contract-corrections/shopware/post-account-register.json) |
| 核心 | POST | `/checkout/cart/line-item/delete` | 移除購物車商品 API | [JSON](api-extension/contract-corrections/shopware/post-checkout-cart-line-item-delete.json) |
| 核心 | POST | `/checkout/cart/line-item` | 新增商品至購物車 API | [JSON](api-extension/contract-corrections/shopware/post-checkout-cart-line-item.json) |
| 核心 | POST | `/checkout/order` | 建立訂單 API | [JSON](api-extension/contract-corrections/shopware/post-checkout-order.json) |
| 核心 | POST | `/product-listing/{categoryId}` | 查詢分類商品 API | [JSON](api-extension/contract-corrections/shopware/post-product-listing-categoryid.json) |
| 核心 | POST | `/product/{productId}` | 取得單一商品 API | [JSON](api-extension/contract-corrections/shopware/post-product-productid.json) |
| 核心 | POST | `/product` | 依條件查詢商品 API | [JSON](api-extension/contract-corrections/shopware/post-product.json) |
| 核心 | POST | `/search` | 搜尋商品 API | [JSON](api-extension/contract-corrections/shopware/post-search.json) |
| 核心 | PATCH | `/checkout/cart/line-item` | 更新購物車品項 API | [JSON](selected-api-contracts/shopware/patch-checkout-cart-line-item.json) |
| 核心 | PATCH | `/context` | 更新購物情境設定 API | [JSON](selected-api-contracts/shopware/patch-context.json) |
| 核心 | POST | `/order` | 查詢顧客訂單 API | [JSON](selected-api-contracts/shopware/post-order.json) |
| 流程支援 | GET | `/context` | 取得購物情境 API | [JSON](selected-api-contracts/shopware/get-context.json) |
| 流程支援 | GET | `/payment-method` | 查詢付款方式 API | [JSON](selected-api-contracts/shopware/get-payment-method.json) |
| 流程支援 | GET | `/shipping-method` | 查詢配送方式 API | [JSON](selected-api-contracts/shopware/get-shipping-method.json) |

## sylius：22 個操作

[用途與填寫參數](selected-api-contracts/sylius/API_parameters.md)

| 角色 | Method | Path | 中文標題 | 採用契約 |
|---|---|---|---|---|
| 核心 | GET | `/api/v2/shop/addresses/{id}` | 取得單一地址 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-addresses-id.json) |
| 核心 | GET | `/api/v2/shop/addresses` | 取得地址清單 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-addresses.json) |
| 核心 | GET | `/api/v2/shop/orders/{tokenValue}/items` | 取得訂單項目清單 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-orders-tokenvalue-items.json) |
| 核心 | GET | `/api/v2/shop/orders/{tokenValue}` | 取得單一訂單 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-orders-tokenvalue.json) |
| 核心 | GET | `/api/v2/shop/orders` | 取得訂單清單 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-orders.json) |
| 核心 | GET | `/api/v2/shop/payment-methods` | 取得付款方式清單 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-payment-methods.json) |
| 核心 | GET | `/api/v2/shop/products-by-slug/{slug}` | 依網址識別字串取得商品 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-products-by-slug-slug.json) |
| 核心 | GET | `/api/v2/shop/products/{code}` | 依商品代碼取得商品 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-products-code.json) |
| 核心 | GET | `/api/v2/shop/products` | 取得商品清單 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-products.json) |
| 核心 | PATCH | `/api/v2/shop/orders/{tokenValue}/complete` | 更新訂單 API | [JSON](selected-api-contracts/sylius/patch-api-v2-shop-orders-tokenvalue-complete.json) |
| 核心 | POST | `/api/v2/shop/addresses` | 建立地址 API | [JSON](selected-api-contracts/sylius/post-api-v2-shop-addresses.json) |
| 核心 | POST | `/api/v2/shop/customers/token` | 顧客登入 API | [JSON](selected-api-contracts/sylius/post-api-v2-shop-customers-token.json) |
| 核心 | POST | `/api/v2/shop/customers` | 建立顧客 API | [JSON](selected-api-contracts/sylius/post-api-v2-shop-customers.json) |
| 核心 | POST | `/api/v2/shop/orders/{tokenValue}/items` | 建立訂單或新增訂單項目 API | [JSON](selected-api-contracts/sylius/post-api-v2-shop-orders-tokenvalue-items.json) |
| 核心 | POST | `/api/v2/shop/orders` | 建立購物車 API | [JSON](selected-api-contracts/sylius/post-api-v2-shop-orders.json) |
| 核心 | PUT | `/api/v2/shop/orders/{tokenValue}` | 更新購物車地址與聯絡資料 API | [JSON](selected-api-contracts/sylius/put-api-v2-shop-orders-tokenvalue.json) |
| 核心 | PATCH | `/api/v2/shop/orders/{tokenValue}/items/{orderItemId}` | 更新購物車品項數量 API | [JSON](selected-api-contracts/sylius/patch-api-v2-shop-orders-tokenvalue-items-orderitemid.json) |
| 核心 | DELETE | `/api/v2/shop/orders/{tokenValue}/items/{orderItemId}` | 移除購物車品項 API | [JSON](selected-api-contracts/sylius/delete-api-v2-shop-orders-tokenvalue-items-orderitemid.json) |
| 核心 | PATCH | `/api/v2/shop/orders/{tokenValue}/shipments/{shipmentId}` | 設定訂單配送方式 API | [JSON](selected-api-contracts/sylius/patch-api-v2-shop-orders-tokenvalue-shipments-shipmentid.json) |
| 核心 | PATCH | `/api/v2/shop/orders/{tokenValue}/payments/{paymentId}` | 設定訂單付款方式 API | [JSON](selected-api-contracts/sylius/patch-api-v2-shop-orders-tokenvalue-payments-paymentid.json) |
| 流程支援 | GET | `/api/v2/shop/orders/{tokenValue}/shipments/{shipmentId}/methods` | 查詢此配送紀錄的可用方式 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-orders-tokenvalue-shipments-shipmentid-methods.json) |
| 流程支援 | GET | `/api/v2/shop/orders/{tokenValue}/payments/{paymentId}/methods` | 查詢此付款紀錄的可用方式 API | [JSON](selected-api-contracts/sylius/get-api-v2-shop-orders-tokenvalue-payments-paymentid-methods.json) |

## 注意事項

- Shopware GET /checkout/gateway 屬選用；POST /order 已納入查單。
- 原始規格、保留的原拆分檔與實際採用的修正版分開保存。16 份修正版的原因見 [契約補充](api-extension/existing-api-supplements.md)。
- 平台版本與正常購物流程未固定／驗證前，不開始宣稱正式資料收集就緒。完整順序見 [實施計畫](api-extension/plan.md)。

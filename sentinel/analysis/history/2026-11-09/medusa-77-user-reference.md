# Medusa 77 個 API：用途、要填的參數與含意

> 部署核對（2026-11-08）：已對 8000 進行部分唯讀抽查，尚未核對全部 77 個操作。`GET /store/locales` 實際回傳 404，與這份規格的操作清單存在差異。詳見 [部署核對紀錄](MSDSS_部署核對紀錄.md)。

「必填」依來源規格；「依業務條件」表示文件沒有完整列出限制。Header 的公開金鑰與登入憑證不相同。

## 01. 確認電子郵件驗證

`POST /auth/customer/emailpass/verification/confirm`

**用途：** 提交寄到電子郵件的驗證 token，完成 emailpass 驗證流程中的信箱確認。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Body：token | 必填 | 寄送到電子郵件的驗證 token |

## 02. 列出顧客認證提供者

`GET /auth/customer/providers`

**用途：** 讓前端取得可使用的登入方式，例如電子郵件密碼或已設定的第三方提供者。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| 無文件列出的輸入參數 | — | 直接呼叫；仍依實際部署條件 |

## 03. 顧客登入／開始認證

`POST /auth/customer/{auth_provider}`

**用途：** 使用指定認證提供者驗證身分。emailpass 通常接收 email、password；第三方登入可能回傳 location，要求前端跳轉。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：auth_provider | 必填 | 認證提供者識別碼，例如 emailpass |
| Body：email | 使用 emailpass 時依提供者要求 | 電子郵件帳號 |
| Body：password | 使用 emailpass 時依提供者要求 | 登入密碼，或 update 時要設定的新密碼；不送入模型與一般日誌 |
| Body：callback_url | 部分第三方提供者選填 | 認證後返回的前端網址；依提供者設定 |

## 04. 完成第三方登入回呼驗證

`POST /auth/customer/{auth_provider}/callback`

**用途：** 第三方登入返回前端後，將 code、state、error 等查詢資料傳給這個 API，驗證後取得認證 token。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：auth_provider | 必填 | 認證提供者識別碼，例如 emailpass |
| Query：code、state、error 等 | 依第三方實際回傳，不是全部同時必填 | 將第三方返回的查詢參數傳入此 API，讓後端驗證認證流程 |

## 05. 取得註冊用 JWT

`POST /auth/customer/{auth_provider}/register`

**用途：** 先建立或準備認證身分，取得可用於後續顧客註冊的 token。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：auth_provider | 必填 | 認證提供者識別碼，例如 emailpass |
| Body：email | 使用 emailpass 時依提供者要求 | 電子郵件帳號 |
| Body：password | 使用 emailpass 時依提供者要求 | 登入密碼，或 update 時要設定的新密碼；不送入模型與一般日誌 |

## 06. 要求產生重設密碼 token

`POST /auth/customer/{auth_provider}/reset-password`

**用途：** 以 identifier 指定認證提供者識別的帳號，要求產生重設密碼 token，並發出 auth.password_reset 事件。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：auth_provider | 必填 | 認證提供者識別碼，例如 emailpass |
| Body：identifier | 必填 | 帳號在認證提供者中的識別值；emailpass 通常是 email |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |

## 07. 使用 token 重設密碼

`POST /auth/customer/{auth_provider}/update`

**用途：** 在 Authorization 帶入重設密碼 token，再提交提供者需要的新密碼等資料。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：auth_provider | 必填 | 認證提供者識別碼，例如 emailpass |
| Header：Authorization | 必填 | Bearer 後接重設密碼 token |
| Body：email | 使用 emailpass 時依提供者要求 | 電子郵件帳號 |
| Body：password | 使用 emailpass 時依提供者要求 | 登入密碼，或 update 時要設定的新密碼；不送入模型與一般日誌 |

## 08. 驗證登入時的 MFA 挑戰

`POST /auth/mfa/challenges/{id}/verify`

**用途：** 對登入流程產生的 challenge 提交 method 與 code，成功後完成後續認證。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | MFA 挑戰識別碼 |
| Body：method | 必填 | MFA 驗證方式；不是 HTTP method |
| Body：code | 必填 | 此驗證流程要求的驗證碼 |

## 09. 列出已登錄的 MFA 因子

`GET /auth/mfa/factors`

**用途：** 取得目前身分的 MFA 因子，包含等待確認與已啟用項目。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| 登入憑證 | 必填；方式依實作 | 此操作要求認證；來源未完整列出標頭方案，需核對部署 |

## 10. 開始綁定 MFA 因子

`POST /auth/mfa/factors`

**用途：** 以 provider 建立新的 MFA 因子，可帶 label、issuer、metadata；TOTP 提供者可能回傳設定用 secret 與 otpauth_url。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| 登入憑證 | 必填；方式依實作 | 此操作要求認證；來源未完整列出標頭方案，需核對部署 |
| Body：provider | 必填 | MFA 提供者識別碼 |
| Body：label | 選填／依業務條件 | MFA 因子等資源的顯示標籤 |
| Body：issuer | 選填／依業務條件 | 驗證器顯示的簽發者名稱 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |

## 11. 停用 MFA 因子

`DELETE /auth/mfa/factors/{id}`

**用途：** 停用指定 MFA factor，之後該因子不能再驗證登入挑戰。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | MFA 因子識別碼 |
| 登入憑證 | 必填；方式依實作 | 此操作要求認證；來源未完整列出標頭方案，需核對部署 |
| Body：method | 選填／依業務條件 | MFA 驗證方式；不是 HTTP method |
| Body：code | 選填／依業務條件 | 此驗證流程要求的驗證碼 |

## 12. 確認並啟用 MFA 因子

`POST /auth/mfa/factors/{id}/verify`

**用途：** 輸入剛綁定因子產生的 code，確認設定正確並啟用。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | MFA 因子識別碼 |
| 登入憑證 | 必填；方式依實作 | 此操作要求認證；來源未完整列出標頭方案，需核對部署 |
| Body：code | 必填 | 此驗證流程要求的驗證碼 |

## 13. 重新產生 MFA 恢復碼

`POST /auth/mfa/recovery-codes`

**用途：** 為目前身分產生單次使用的備援登入碼，可帶 count 指定數量。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| 登入憑證 | 必填；方式依實作 | 此操作要求認證；來源未完整列出標頭方案，需核對部署 |
| Body：count | 選填／依業務條件 | 要產生的 MFA 恢復碼數量；描述要求 1～50，省略時用提供者設定 |

## 14. 建立 Cookie 登入工作階段

`POST /auth/session`

**用途：** 先取得登入 JWT，再用它建立以 Cookie session ID 維持的登入狀態。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Authorization | 必填 | Bearer 後接先前登入取得的 JWT，用來建立 Cookie Session |

## 15. 結束 Cookie 登入工作階段

`DELETE /auth/session`

**用途：** 刪除先前建立的 Cookie session，使該工作階段登出。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Cookie：connect.sid | 依部署的工作階段設定 | 要結束的登入工作階段識別值 |

## 16. 更新認證 token

`POST /auth/token/refresh`

**用途：** 要求更新顧客認證 token，用於延續登入或取得更新後的使用者資訊。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| 登入憑證 | 必填；方式依實作 | 此操作要求認證；來源未完整列出標頭方案，需核對部署 |

## 17. 確認通用驗證碼

`POST /auth/verification/confirm`

**用途：** 提交 code 與可能需要的 code_provider，完成信箱或自訂手機等驗證流程。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Body：code | 必填 | 此驗證流程要求的驗證碼 |
| Body：code_provider | 選填／依業務條件 | 產生與驗證代碼的提供者 |

## 18. 要求產生通用驗證碼

`POST /auth/verification/request`

**用途：** 以 entity_id、entity_type、code_provider 建立驗證要求，產生驗證碼並發出 auth.verification_requested 事件。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Body：entity_id | 必填 | 要驗證的對象識別值，例如電子郵件地址 |
| Body：entity_type | 必填 | 驗證對象種類，例如 email 或 phone_number |
| Body：code_provider | 必填 | 產生與驗證代碼的提供者 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |

## 19. 建立購物車

`POST /store/carts`

**用途：** 建立購物車，可提供 region、幣別、地址、email、初始品項、銷售渠道與 metadata。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：region_id | 選填／依業務條件 | 商務區域識別碼 |
| Body：shipping_address | 選填／依業務條件 | 配送地址物件 |
| Body：shipping_address.id | 填寫此物件時必填 | 資源識別碼；意義由目前 API 決定 |
| Body：shipping_address.customer_id | 選填／依業務條件 | 顧客識別碼 |
| Body：shipping_address.first_name | 選填／依業務條件 | 名字 |
| Body：shipping_address.last_name | 選填／依業務條件 | 姓氏 |
| Body：shipping_address.phone | 選填／依業務條件 | 電話；測試需用假資料 |
| Body：shipping_address.company | 選填／依業務條件 | 公司／組織 |
| Body：shipping_address.address_1 | 選填／依業務條件 | 地址第一行 |
| Body：shipping_address.address_2 | 選填／依業務條件 | 地址第二行 |
| Body：shipping_address.city | 選填／依業務條件 | 城市 |
| Body：shipping_address.country_code | 選填／依業務條件 | 國家代碼 |
| Body：shipping_address.province | 選填／依業務條件 | 省／州／行政區 |
| Body：shipping_address.postal_code | 選填／依業務條件 | 郵遞區號 |
| Body：shipping_address.metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |
| Body：shipping_address.created_at | 填寫此物件時必填 | 建立時間篩選 |
| Body：shipping_address.updated_at | 填寫此物件時必填 | 更新時間篩選 |
| Body：billing_address | 選填／依業務條件 | 帳單地址物件 |
| Body：billing_address.id | 填寫此物件時必填 | 資源識別碼；意義由目前 API 決定 |
| Body：billing_address.customer_id | 選填／依業務條件 | 顧客識別碼 |
| Body：billing_address.first_name | 選填／依業務條件 | 名字 |
| Body：billing_address.last_name | 選填／依業務條件 | 姓氏 |
| Body：billing_address.phone | 選填／依業務條件 | 電話；測試需用假資料 |
| Body：billing_address.company | 選填／依業務條件 | 公司／組織 |
| Body：billing_address.address_1 | 選填／依業務條件 | 地址第一行 |
| Body：billing_address.address_2 | 選填／依業務條件 | 地址第二行 |
| Body：billing_address.city | 選填／依業務條件 | 城市 |
| Body：billing_address.country_code | 選填／依業務條件 | 國家代碼 |
| Body：billing_address.province | 選填／依業務條件 | 省／州／行政區 |
| Body：billing_address.postal_code | 選填／依業務條件 | 郵遞區號 |
| Body：billing_address.metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |
| Body：billing_address.created_at | 填寫此物件時必填 | 建立時間篩選 |
| Body：billing_address.updated_at | 填寫此物件時必填 | 更新時間篩選 |
| Body：email | 選填／依業務條件 | 電子郵件地址 |
| Body：currency_code | 選填／依業務條件 | 幣別代碼 |
| Body：items | 選填／依業務條件 | 品項陣列；結構依目前操作 |
| Body：items[].id | 填寫此物件時必填 | 資源識別碼；意義由目前 API 決定 |
| Body：items[].quantity | 填寫此物件時必填 | 數量 |
| Body：items[].variant_id | 選填／依業務條件 | 可購買商品變體的識別碼 |
| Body：sales_channel_id | 選填／依業務條件 | 銷售渠道識別碼 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |
| Body：additional_data | 選填／依業務條件 | 交給後端 workflow 的額外自訂資料 |

## 20. 取得購物車

`GET /store/carts/{id}`

**用途：** 讀取指定購物車、品項與金額等資訊，可依文件提供的 fields 選取資料。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 21. 更新購物車

`POST /store/carts/{id}`

**用途：** 更新 email、region、幣別、地址、渠道等購物車資料。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：region_id | 選填／依業務條件 | 商務區域識別碼 |
| Body：customer_id | 選填／依業務條件 | 顧客識別碼 |
| Body：sales_channel_id | 選填／依業務條件 | 銷售渠道識別碼 |
| Body：email | 選填／依業務條件 | 電子郵件地址 |
| Body：currency_code | 選填／依業務條件 | 幣別代碼 |
| Body：shipping_address_id | 選填／依業務條件 | 配送地址識別碼 |
| Body：billing_address_id | 選填／依業務條件 | 帳單地址識別碼 |
| Body：billing_address | 選填／依業務條件 | 帳單地址物件 |
| Body：shipping_address | 選填／依業務條件 | 配送地址物件 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |
| Body：additional_data | 選填／依業務條件 | 交給後端 workflow 的額外自訂資料 |

## 22. 完成結帳並建立訂單

`POST /store/carts/{id}/complete`

**用途：** 嘗試將購物車轉為訂單。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 23. 將購物車連到目前顧客

`POST /store/carts/{id}/customer`

**用途：** 顧客先以訪客建立購物車、登入後，將購物車所屬顧客改成目前登入身分。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |
| Body：additional_data | 選填／依業務條件 | 交給後端 workflow 的額外自訂資料 |

## 24. 套用禮物卡

`POST /store/carts/{id}/gift-cards`

**用途：** 把 code 指定的 gift card 加到購物車，參與結帳抵用計算。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：code | 必填 | 要套用或移除的禮物卡代碼 |

## 25. 移除禮物卡

`DELETE /store/carts/{id}/gift-cards`

**用途：** 以 JSON 本文的 code 移除購物車先前套用的禮物卡。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：code | 必填 | 要套用或移除的禮物卡代碼 |

## 26. 加入商品變體

`POST /store/carts/{id}/line-items`

**用途：** 用 variant_id 與 quantity 將可購買的商品變體加入購物車。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：variant_id | 必填 | 可購買商品變體的識別碼 |
| Body：quantity | 必填 | 數量 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |
| Body：additional_data | 選填／依業務條件 | 交給後端 workflow 的額外自訂資料 |

## 27. 修改購物車品項

`POST /store/carts/{id}/line-items/{line_id}`

**用途：** 用 line_id 指定購物車項目，更新 quantity 與可選 metadata。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Path：line_id | 必填 | 購物車品項識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：quantity | 必填 | 數量 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |
| Body：additional_data | 選填／依業務條件 | 交給後端 workflow 的額外自訂資料 |

## 28. 移除購物車品項

`DELETE /store/carts/{id}/line-items/{line_id}`

**用途：** 移除購物車中的一筆 line item。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 購物車識別碼 |
| Path：line_id | 必填 | 購物車品項識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 29. 套用優惠碼

`POST /store/carts/{id}/promotions`

**用途：** 以 promo_codes 陣列將一個或多個優惠活動加入購物車。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：promo_codes | 必填 | 優惠碼字串陣列 |

## 30. 移除優惠碼

`DELETE /store/carts/{id}/promotions`

**用途：** 以 promo_codes 陣列移除購物車上的優惠。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：promo_codes | 必填 | 優惠碼字串陣列 |

## 31. 選擇購物車配送方式

`POST /store/carts/{id}/shipping-methods`

**用途：** 以 option_id 選定配送選項，建立或更新購物車使用的配送方式，必要時帶提供者資料 data。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Body：option_id | 必填（分支 1） | 配送選項識別碼 |
| Body：data | 選填／依業務條件（分支 1） | 提供者需要的結構化自訂資料 |
| Body：additional_data | 選填／依業務條件（分支 1） | 交給後端 workflow 的額外自訂資料 |
| Body：additional_data | 選填／依業務條件（分支 2） | 交給後端 workflow 的額外自訂資料 |

## 32. 使用商店抵用額度

`POST /store/carts/{id}/store-credits`

**用途：** 以 amount 指定要套用到購物車的商店抵用額度。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：amount | 必填 | 金額；需核對幣別與模組的精度 |

## 33. 重算購物車稅額

`POST /store/carts/{id}/taxes`

**用途：** 重新計算購物車各項稅務明細與金額。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 購物車識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |

## 34. 列出商品集合

`GET /store/collections`

**用途：** 取得可用的商品集合，可依 handle 等條件篩選、分頁或排序。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：title | 選填 | 標題 |
| Query：created_at | 選填 | 建立時間篩選 |
| Query：updated_at | 選填 | 更新時間篩選 |
| Query：handle | 選填 | 適合網址或人類辨識的代稱 |
| Query：q | 選填 | 搜尋字詞 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：id | 選填 | 要篩選的資源識別碼 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：external_id | 選填 | 外部系統對應的識別碼 |

## 35. 取得單一商品集合

`GET /store/collections/{id}`

**用途：** 依 collection ID 取得集合資料與可選關聯欄位。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 商品集合識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 36. 列出幣別資料

`GET /store/currencies`

**用途：** 取得 currency 資源列表，可篩選、分頁與排序。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：q | 選填 | 搜尋字詞 |
| Query：code | 選填 | 驗證碼或兌換碼，依 API 用途決定 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 37. 取得單一幣別

`GET /store/currencies/{code}`

**用途：** 依幣別 code 查詢資料，例如規格中允許的幣別代碼。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：code | 必填 | 幣別代碼，例如 usd；不是驗證碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 38. 建立顧客資料

`POST /store/customers`

**用途：** 先取得註冊 JWT，再建立與認證身分連結的 customer 資料，可含姓名、電話、公司與 metadata。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |
| Body：email | 選填／依業務條件 | 電子郵件地址 |
| Body：company_name | 選填／依業務條件 | 公司名稱 |
| Body：first_name | 選填／依業務條件 | 名字 |
| Body：last_name | 選填／依業務條件 | 姓氏 |
| Body：phone | 選填／依業務條件 | 電話；測試需用假資料 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |

## 39. 取得目前顧客

`GET /store/customers/me`

**用途：** 以登入身分取得自己的顧客資料。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |

## 40. 更新目前顧客

`POST /store/customers/me`

**用途：** 更新目前顧客的姓名、公司、電話與 metadata 等欄位。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |
| Body：company_name | 選填／依業務條件 | 公司名稱 |
| Body：first_name | 選填／依業務條件 | 名字 |
| Body：last_name | 選填／依業務條件 | 姓氏 |
| Body：phone | 選填／依業務條件 | 電話；測試需用假資料 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |

## 41. 列出自己的地址

`GET /store/customers/me/addresses`

**用途：** 取得目前顧客保存的地址，支援文件列出的條件、分頁與排序。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：city | 選填 | 城市 |
| Query：postal_code | 選填 | 郵遞區號 |
| Query：country_code | 選填 | 國家代碼 |
| Query：q | 選填 | 搜尋字詞 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |

## 42. 新增自己的地址

`POST /store/customers/me/addresses`

**用途：** 建立地址簿紀錄，可包含姓名、國家、城市、郵遞區號與預設配送／帳單旗標。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |
| Body：first_name | 選填／依業務條件 | 名字 |
| Body：last_name | 選填／依業務條件 | 姓氏 |
| Body：phone | 選填／依業務條件 | 電話；測試需用假資料 |
| Body：company | 選填／依業務條件 | 公司／組織 |
| Body：address_1 | 選填／依業務條件 | 地址第一行 |
| Body：address_2 | 選填／依業務條件 | 地址第二行 |
| Body：city | 選填／依業務條件 | 城市 |
| Body：country_code | 選填／依業務條件 | 國家代碼 |
| Body：province | 選填／依業務條件 | 省／州／行政區 |
| Body：postal_code | 選填／依業務條件 | 郵遞區號 |
| Body：address_name | 選填／依業務條件 | 地址名稱，例如住家 |
| Body：is_default_shipping | 選填／依業務條件 | 是否為預設配送地址 |
| Body：is_default_billing | 選填／依業務條件 | 是否為預設帳單地址 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |

## 43. 取得自己的一筆地址

`GET /store/customers/me/addresses/{address_id}`

**用途：** 依 address_id 取得目前顧客地址簿中的紀錄。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：address_id | 必填 | 顧客地址識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |

## 44. 更新自己的一筆地址

`POST /store/customers/me/addresses/{address_id}`

**用途：** 更新指定地址與預設配送／帳單設定等資訊。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：address_id | 必填 | 顧客地址識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |
| Body：first_name | 選填／依業務條件 | 名字 |
| Body：last_name | 選填／依業務條件 | 姓氏 |
| Body：phone | 選填／依業務條件 | 電話；測試需用假資料 |
| Body：company | 選填／依業務條件 | 公司／組織 |
| Body：address_1 | 選填／依業務條件 | 地址第一行 |
| Body：address_2 | 選填／依業務條件 | 地址第二行 |
| Body：city | 選填／依業務條件 | 城市 |
| Body：country_code | 選填／依業務條件 | 國家代碼 |
| Body：province | 選填／依業務條件 | 省／州／行政區 |
| Body：postal_code | 選填／依業務條件 | 郵遞區號 |
| Body：address_name | 選填／依業務條件 | 地址名稱，例如住家 |
| Body：is_default_shipping | 選填／依業務條件 | 是否為預設配送地址 |
| Body：is_default_billing | 選填／依業務條件 | 是否為預設帳單地址 |
| Body：metadata | 選填／依業務條件 | 自訂鍵值資料；不等於任意指令 |

## 45. 刪除自己的一筆地址

`DELETE /store/customers/me/addresses/{address_id}`

**用途：** 移除目前顧客地址簿中的指定紀錄。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：address_id | 必填 | 顧客地址識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |

## 46. 查詢禮物卡

`GET /store/gift-cards/{idOrCode}`

**用途：** 用禮物卡 ID 或代碼查詢可回傳的禮物卡資訊。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：idOrCode | 必填 | 禮物卡 ID 或兌換代碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 47. 列出支援語系

`GET /store/locales`

**部署核對：** `http://161.33.154.211:8000/store/locales` 本次回傳 404（Cannot GET /store/locales）。目前不能將此操作列為已部署可用；原因需核對專案版本、路由與模組設定。

**用途：** 取得商店提供的語系列表，供前端語言選擇使用。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 48. 列出自己的訂單

`GET /store/orders`

**用途：** 取得目前登入顧客的訂單列表，依文件條件篩選、分頁與排序。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：id | 選填 | 要篩選的資源識別碼 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：status | 選填 | 資源狀態；不是 HTTP 狀態碼 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |

## 49. 取得單筆訂單

`GET /store/orders/{id}`

**用途：** 依訂單 ID 讀取訂單，規格保留訪客下單後查確認頁的用途。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 訂單識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 50. 接受訂單歸戶轉移

`POST /store/orders/{id}/transfer/accept`

**用途：** 使用先前轉移流程產生的 token，接受把訂單歸到指定顧客帳戶。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 訂單識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：token | 必填 | 訂單轉移流程產生的確認 token |

## 51. 取消先前的訂單轉移要求

`POST /store/orders/{id}/transfer/cancel`

**用途：** 登入顧客取消先前提出的訂單歸戶要求。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 訂單識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |

## 52. 拒絕訂單歸戶轉移

`POST /store/orders/{id}/transfer/decline`

**用途：** 以 token 拒絕先前要求的訂單轉移。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 訂單識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：token | 必填 | 訂單轉移流程產生的確認 token |

## 53. 要求將訂單歸戶

`POST /store/orders/{id}/transfer/request`

**用途：** 登入顧客要求把訂單移到自己帳戶，可帶 description 與 update_order_email。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 訂單識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |
| Body：description | 選填／依業務條件 | 描述文字 |
| Body：update_order_email | 選填／依業務條件 | 轉移訂單時是否更新訂單 email |

## 54. 建立付款集合

`POST /store/payment-collections`

**用途：** 以 cart_id 建立承載該購物車付款工作階段的 payment collection。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：cart_id | 必填 | 購物車識別碼 |

## 55. 初始化付款工作階段

`POST /store/payment-collections/{id}/payment-sessions`

**用途：** 選擇 provider_id，向付款提供者初始化 session，可提交提供者需要的 data。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 付款集合識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：provider_id | 必填 | 付款等模組的提供者識別碼 |
| Body：data | 選填／依業務條件 | 提供者需要的結構化自訂資料 |

## 56. 列出區域可用付款提供者

`GET /store/payment-providers`

**用途：** 必須以 region_id 查詢該區域啟用的付款提供者。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：region_id | 必填 | 商務區域識別碼 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 57. 列出商品分類

`GET /store/product-categories`

**用途：** 取得商品分類，依文件支援的條件篩選、分頁與排序。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：q | 選填 | 搜尋字詞 |
| Query：id | 選填 | 要篩選的資源識別碼 |
| Query：description | 選填 | 描述文字 |
| Query：handle | 選填 | 適合網址或人類辨識的代稱 |
| Query：parent_category_id | 選填 | 父分類識別碼 |
| Query：include_ancestors_tree | 選填 | 是否要求展開祖先分類樹 |
| Query：include_descendants_tree | 選填 | 是否要求展開後代分類樹 |
| Query：created_at | 選填 | 建立時間篩選 |
| Query：updated_at | 選填 | 更新時間篩選 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：name | 選填 | 名稱篩選值 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：external_id | 選填 | 外部系統對應的識別碼 |

## 58. 取得單一商品分類

`GET /store/product-categories/{id}`

**用途：** 依分類 ID 讀取資料，可選取關聯欄位。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 商品分類識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：include_ancestors_tree | 選填 | 是否要求展開祖先分類樹 |
| Query：include_descendants_tree | 選填 | 是否要求展開後代分類樹 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 59. 列出商品選項

`GET /store/product-options`

**用途：** 取得商品規格維度，例如尺寸、顏色等選項。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：q | 選填 | 搜尋字詞 |
| Query：title | 選填 | 標題 |
| Query：is_exclusive | 選填 | 是否使用排他篩選，依目前查詢資源定義 |
| Query：created_at | 選填 | 建立時間篩選 |
| Query：updated_at | 選填 | 更新時間篩選 |
| Query：deleted_at | 選填 | 刪除時間篩選 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：id | 選填 | 要篩選的資源識別碼 |

## 60. 取得單一商品選項

`GET /store/product-options/{id}`

**用途：** 依 option ID 讀取該規格維度及所選關聯。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 商品規格選項識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |

## 61. 列出商品標籤

`GET /store/product-tags`

**用途：** 取得用於描述或篩選商品的標籤列表。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：q | 選填 | 搜尋字詞 |
| Query：id | 選填 | 要篩選的資源識別碼 |
| Query：value | 選填 | 標籤或選項的值，依 API 對象決定 |
| Query：created_at | 選填 | 建立時間篩選 |
| Query：updated_at | 選填 | 更新時間篩選 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：external_id | 選填 | 外部系統對應的識別碼 |

## 62. 取得單一商品標籤

`GET /store/product-tags/{id}`

**用途：** 依 tag ID 取得標籤資訊。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 商品標籤識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 63. 列出商品類型

`GET /store/product-types`

**用途：** 取得商店建立的商品類型列表。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：q | 選填 | 搜尋字詞 |
| Query：id | 選填 | 要篩選的資源識別碼 |
| Query：value | 選填 | 標籤或選項的值，依 API 對象決定 |
| Query：created_at | 選填 | 建立時間篩選 |
| Query：updated_at | 選填 | 更新時間篩選 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：external_id | 選填 | 外部系統對應的識別碼 |

## 64. 取得單一商品類型

`GET /store/product-types/{id}`

**用途：** 依商品 type ID 取得資料。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 商品類型識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 65. 列出商品變體

`GET /store/product-variants`

**用途：** 查詢實際可購買的 variant 資料，例如某商品的某尺寸與顏色組合。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：sku | 選填 | 庫存管理代碼 |
| Query：manage_inventory | 選填 | 篩選是否由系統管理庫存的商品變體 |
| Query：allow_backorder | 選填 | 篩選是否允許缺貨後繼續訂購的商品變體 |
| Query：product_id | 選填 | 商品識別碼 |
| Query：q | 選填 | 搜尋字詞 |
| Query：id | 選填 | 要篩選的資源識別碼 |
| Query：options | 選填 | 商品規格選項的篩選條件 |
| Query：created_at | 選填 | 建立時間篩選 |
| Query：updated_at | 選填 | 更新時間篩選 |
| Query：deleted_at | 選填 | 刪除時間篩選 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |

## 66. 商品列表、搜尋與篩選

`GET /store/products`

**用途：** 以 q 搜尋商品的可搜尋欄位，或使用 id、分類等文件列出的篩選；可分頁、排序與選欄位。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：q | 選填 | 搜尋字詞 |
| Query：id | 選填 | 要篩選的資源識別碼 |
| Query：title | 選填 | 標題 |
| Query：handle | 選填 | 適合網址或人類辨識的代稱 |
| Query：is_giftcard | 選填 | 是否為禮物卡商品 |
| Query：collection_id | 選填 | 商品集合識別碼 |
| Query：tag_id | 選填 | 商品標籤識別碼 |
| Query：type_id | 選填 | 商品類型識別碼 |
| Query：created_at | 選填 | 建立時間篩選 |
| Query：updated_at | 選填 | 更新時間篩選 |
| Query：region_id | 選填 | 商務區域識別碼 |
| Query：province | 選填 | 省／州／行政區 |
| Query：sales_channel_id | 選填 | 銷售渠道識別碼 |
| Query：category_id | 選填 | 商品分類識別碼 |
| Query：variants | 選填 | 商品變體的巢狀篩選條件 |
| Query：country_code | 選填 | 國家代碼 |
| Query：cart_id | 選填 | 購物車識別碼 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：external_id | 選填 | 外部系統對應的識別碼 |
| Query：option_value_id | 選填 | 商品規格值的識別碼，例如某個尺寸或顏色值 |
| Query：option_id | 選填 | 配送選項識別碼 |

## 67. 取得單一商品

`GET /store/products/{id}`

**用途：** 依商品 ID 讀取商品、所選變體或關聯資訊，可指定語系。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 商品識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：region_id | 選填 | 商務區域識別碼 |
| Query：country_code | 選填 | 國家代碼 |
| Query：province | 選填 | 省／州／行政區 |
| Query：cart_id | 選填 | 購物車識別碼 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 68. 列出商務區域

`GET /store/regions`

**用途：** 取得 Region 資源，用於結帳幣別、稅務與付款等商務設定。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：q | 選填 | 搜尋字詞 |
| Query：id | 選填 | 要篩選的資源識別碼 |
| Query：name | 選填 | 名稱篩選值 |
| Query：currency_code | 選填 | 幣別代碼 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 69. 取得單一商務區域

`GET /store/regions/{id}`

**用途：** 依 region ID 取得該商務區域資料與選定關聯。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 商務區域識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 70. 列出退貨原因

`GET /store/return-reasons`

**用途：** 取得後端提供的退貨原因清單，可依文件分頁與排序。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 71. 取得單一退貨原因

`GET /store/return-reasons/{id}`

**用途：** 依原因 ID 取得資料與可選關聯。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 退貨原因識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 72. 建立退貨要求

`POST /store/returns`

**用途：** 以 order_id、items、return_shipping 等資料建立訂單品項退貨，後續由管理端處理。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Body：order_id | 必填 | 訂單識別碼 |
| Body：items | 必填 | 品項陣列；結構依目前操作 |
| Body：items[].id | 填寫此物件時必填 | 資源識別碼；意義由目前 API 決定 |
| Body：items[].quantity | 填寫此物件時必填 | 數量 |
| Body：items[].reason_id | 選填／依業務條件 | 退貨原因識別碼 |
| Body：items[].note | 選填／依業務條件 | 備註文字 |
| Body：return_shipping | 必填 | 退貨配送資料 |
| Body：return_shipping.option_id | 填寫此物件時必填 | 配送選項識別碼 |
| Body：return_shipping.price | 選填／依業務條件 | 退貨配送價格；單位與精度依模組確認 |
| Body：note | 選填／依業務條件 | 備註文字 |
| Body：receive_now | 選填／依業務條件 | 是否要求立即標記收貨；需核對部署權限與行為 |
| Body：location_id | 選填／依業務條件 | 庫存／收退貨據點識別碼 |

## 73. 查詢購物車可用配送選項

`GET /store/shipping-options`

**用途：** 以必填 cart_id 取得該購物車適用的配送選項。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：cart_id | 必填 | 購物車識別碼 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：is_return | 選填 | 篩選退貨用途的配送選項 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |

## 74. 計算配送選項價格

`POST /store/shipping-options/{id}/calculate`

**用途：** 以 cart_id 與提供者 data 計算指定配送選項對該購物車的價格。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Path：id | 必填 | 配送選項識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Body：cart_id | 必填 | 購物車識別碼 |
| Body：data | 選填／依業務條件 | 提供者需要的結構化自訂資料 |

## 75. 列出自己的商店額度帳戶

`GET /store/store-credit-accounts`

**用途：** 取得目前顧客的 store credit accounts，可依幣別、時間等條件篩選。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：currency_code | 選填 | 幣別代碼 |
| Query：created_at | 選填 | 建立時間篩選 |
| Query：updated_at | 選填 | 更新時間篩選 |
| Query：limit | 選填 | 每次最多回傳的筆數 |
| Query：offset | 選填 | 略過前面多少筆 |
| Query：order | 選填 | 排序欄位，前綴 - 通常代表降冪 |
| Query：fields | 選填 | 選取回應欄位或展開關聯，並非 SQL 欄位任意查詢 |
| Query：$and | 選填 | 同時符合條件 |
| Query：$or | 選填 | 符合任一條件 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Query：with_deleted | 選填 | 是否要求包含刪除資料；是否可用須核對部署 |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |

## 76. 認領商店額度帳戶

`POST /store/store-credit-accounts/claim`

**用途：** 用 code 把可認領的匿名額度帳戶連結到目前登入顧客。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Header：Content-Type | 使用 JSON 本文時 | application/json |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |
| Body：code | 必填 | 要認領的商店額度帳戶代碼 |

## 77. 取得自己的額度帳戶

`GET /store/store-credit-accounts/{id}`

**用途：** 依 ID 讀取目前顧客的商店額度帳戶。

| 要填的參數 | 必填／選填 | 代表的含意 |
|---|---|---|
| Path：id | 必填 | 商店額度帳戶識別碼 |
| Header：x-publishable-api-key | 必填 | Store API 公開金鑰，用來限定銷售渠道；不等於顧客登入 |
| Header：x-medusa-locale | 選填 | 語系標頭 |
| Query：locale | 選填 | 語系標記，例如 zh-TW |
| Header：Authorization 或 Cookie：connect.sid | 認證擇一 | 有效顧客 JWT 或登入工作階段；POST /store/customers 依描述使用註冊 token |

# Medusa 選定 API 與舊文件核對紀錄

更新日期：2026-11-08（Asia/Taipei）。原 77 API 文件保留，這份是新增的核對結果。

- 舊文件：77 個操作；現行選定：79 個；bundled 規格：79 個。
- 應用套件固定 2.22.4；bundled OpenAPI info.version=2.22.3，兩者不混用。
- 目前既有 9100 容器另經唯讀確認為 Medusa 2.21.0；本次另建 18084 的 2.22.4，兩者資料庫隔離，不能補造舊 8000 測試細節。
- 所有有副作用的本次測試只允許獨立的 127.0.0.1:18084，不操作既有 Medusa／Mirage 資料庫。
- 這次核對 API、契約與正常流程，不使用 Medusa 訓練模型、選特徵或調門檻。

## 舊清單與現行清單差異

- 現行新增 `POST /store/payment-collections/{id}/payment-sessions/{session_id}`；不直接改寫舊文件。
- 現行新增 `POST /store/search`；不直接改寫舊文件。

舊操作在現行規格中缺失：0；選定操作在現行規格中缺失：0。這只證明契約路徑／方法存在，不代表每個操作都已實機成功。

## 逐操作實測狀態

| Method | Path | 舊 77 清單 | 現行契約 | 實測狀態 | 說明／證據 |
|---|---|---|---|---|---|
| POST | `/auth/customer/emailpass/verification/confirm` | 有 | 存在 | 版本差異 | bundled 規格列有，但原生／工作區編譯 route 無對應且本機探查 404；不是業務成功；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| GET | `/auth/customer/providers` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/auth/customer/{auth_provider}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/auth/customer/{auth_provider}/callback` | 有 | 存在 | 前置條件不足 | 沒有郵件／第三方登入／驗證碼送達的完整情境，不能使用虛假 Token 補造成功 |
| POST | `/auth/customer/{auth_provider}/register` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/auth/customer/{auth_provider}/reset-password` | 有 | 存在 | 前置條件不足 | 沒有郵件／第三方登入／驗證碼送達的完整情境，不能使用虛假 Token 補造成功 |
| POST | `/auth/customer/{auth_provider}/update` | 有 | 存在 | 前置條件不足 | 沒有郵件／第三方登入／驗證碼送達的完整情境，不能使用虛假 Token 補造成功 |
| POST | `/auth/mfa/challenges/{id}/verify` | 有 | 存在 | 前置條件不足 | 本次已補入建置期 MFA encryption key，但沒有可由正常登入流程產生的 challenge ID；不能用虛假 ID 的拒絕回應當成成功 |
| GET | `/auth/mfa/factors` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-mfa-cf90592d78914c559ef5c9e935125a1b.json |
| POST | `/auth/mfa/factors` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-mfa-cf90592d78914c559ef5c9e935125a1b.json |
| DELETE | `/auth/mfa/factors/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-mfa-cf90592d78914c559ef5c9e935125a1b.json |
| POST | `/auth/mfa/factors/{id}/verify` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-mfa-cf90592d78914c559ef5c9e935125a1b.json |
| POST | `/auth/mfa/recovery-codes` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-mfa-cf90592d78914c559ef5c9e935125a1b.json |
| POST | `/auth/session` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| DELETE | `/auth/session` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/auth/token/refresh` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/auth/verification/confirm` | 有 | 存在 | 前置條件不足 | 沒有郵件／第三方登入／驗證碼送達的完整情境，不能使用虛假 Token 補造成功 |
| POST | `/auth/verification/request` | 有 | 存在 | 前置條件不足 | 沒有郵件／第三方登入／驗證碼送達的完整情境，不能使用虛假 Token 補造成功 |
| POST | `/store/carts` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/carts/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/carts/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/carts/{id}/complete` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/carts/{id}/customer` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/carts/{id}/gift-cards` | 有 | 存在 | 版本差異 | bundled 規格列有，但原生／工作區編譯 route 無對應且本機探查 404；不是業務成功；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| DELETE | `/store/carts/{id}/gift-cards` | 有 | 存在 | 版本差異 | bundled 規格列有，但原生／工作區編譯 route 無對應且本機探查 404；不是業務成功；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| POST | `/store/carts/{id}/line-items` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/carts/{id}/line-items/{line_id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| DELETE | `/store/carts/{id}/line-items/{line_id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/carts/{id}/promotions` | 有 | 存在 | 尚未測試 | 尚無通過的實機情境；退貨須已履約訂單、移轉須雙方與有效移轉 token、促銷須有效折扣資料 |
| DELETE | `/store/carts/{id}/promotions` | 有 | 存在 | 尚未測試 | 尚無通過的實機情境；退貨須已履約訂單、移轉須雙方與有效移轉 token、促銷須有效折扣資料 |
| POST | `/store/carts/{id}/shipping-methods` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/carts/{id}/store-credits` | 有 | 存在 | 版本差異 | bundled 規格列有，但原生／工作區編譯 route 無對應且本機探查 404；不是業務成功；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| POST | `/store/carts/{id}/taxes` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-probes-0c1adbd9a40140c0b6b7cfddaee6e5cb.json, medusa-probes-3d03f6aeedde419e87ed16e11317beff.json, medusa-probes-48d781ddfc6944bc9a3b5a8fe67eea31.json, medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| GET | `/store/collections` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/collections/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/currencies` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/currencies/{code}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/customers` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/customers/me` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/customers/me` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/customers/me/addresses` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/customers/me/addresses` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/customers/me/addresses/{address_id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/customers/me/addresses/{address_id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| DELETE | `/store/customers/me/addresses/{address_id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/gift-cards/{idOrCode}` | 有 | 存在 | 版本差異 | bundled 規格列有，但原生／工作區編譯 route 無對應且本機探查 404；不是業務成功；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| GET | `/store/locales` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/orders` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/orders/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/orders/{id}/transfer/accept` | 有 | 存在 | 尚未測試 | 尚無通過的實機情境；退貨須已履約訂單、移轉須雙方與有效移轉 token、促銷須有效折扣資料 |
| POST | `/store/orders/{id}/transfer/cancel` | 有 | 存在 | 尚未測試 | 尚無通過的實機情境；退貨須已履約訂單、移轉須雙方與有效移轉 token、促銷須有效折扣資料 |
| POST | `/store/orders/{id}/transfer/decline` | 有 | 存在 | 尚未測試 | 尚無通過的實機情境；退貨須已履約訂單、移轉須雙方與有效移轉 token、促銷須有效折扣資料 |
| POST | `/store/orders/{id}/transfer/request` | 有 | 存在 | 尚未測試 | 尚無通過的實機情境；退貨須已履約訂單、移轉須雙方與有效移轉 token、促銷須有效折扣資料 |
| POST | `/store/payment-collections` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/payment-collections/{id}/payment-sessions` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/payment-collections/{id}/payment-sessions/{session_id}` | 無 | 存在 | 前置條件不足 | 原生 pp_system_default 接受 client_data 但不回傳／保存此提供者特定資料；只確認路由受理與 session 身分一致，不能宣稱已驗證 PSP 客戶端資料變更。；medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/payment-providers` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/product-categories` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/product-categories/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/product-options` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/product-options/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/product-tags` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/product-tags/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/product-types` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/product-types/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/product-variants` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/products` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/products/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/regions` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/regions/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/return-reasons` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| GET | `/store/return-reasons/{id}` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/returns` | 有 | 存在 | 尚未測試 | 尚無通過的實機情境；退貨須已履約訂單、移轉須雙方與有效移轉 token、促銷須有效折扣資料 |
| POST | `/store/search` | 無 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| GET | `/store/shipping-options` | 有 | 存在 | 成功 | 有真實回應與業務斷言證據（主流程或獨立功能探查）；medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json, medusa-72caa767eed84dcead80c23929ac09b5.json |
| POST | `/store/shipping-options/{id}/calculate` | 有 | 存在 | 前置條件不足 | manual 提供者 canCalculate()=false、calculatePrice() 明確拋錯；本機 calculate 回 500。需要支援計價的提供者；固定費率配送與結帳已成功。；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| GET | `/store/store-credit-accounts` | 有 | 存在 | 版本差異 | bundled 規格列有，但原生／工作區編譯 route 無對應且本機探查 404；不是業務成功；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| POST | `/store/store-credit-accounts/claim` | 有 | 存在 | 版本差異 | bundled 規格列有，但原生／工作區編譯 route 無對應且本機探查 404；不是業務成功；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |
| GET | `/store/store-credit-accounts/{id}` | 有 | 存在 | 版本差異 | bundled 規格列有，但原生／工作區編譯 route 無對應且本機探查 404；不是業務成功；medusa-probes-aea1423a6a974623bab0a42339eb0e99.json |

## 解讀限制

統計：版本差異 8、成功 56、前置條件不足 8、尚未測試 7。MFA 因建置期金鑰已補入，TOTP 因子註冊、驗證、備援碼與停用均已成功；只有 challenge verify 仍因缺少真實 challenge ID 保持前置條件不足。

路徑／方法、文件版本與實機情境分開核對。尚未逐欄確認的舊參數含義不因路徑存在而視為正確。具體參數錯誤與證據見 [Medusa_API_參數差異.md](Medusa_API_參數差異.md)。MFA、郵件驗證、第三方登入及重設流程需要各自前置條件，不能使用虛假 Token 或 401／404 代替驗證。路由探查可使用明確標示的未發行禮卡／儲值帳戶識別值，只用於路由與程式碼比對，從不當成正常業務成功。

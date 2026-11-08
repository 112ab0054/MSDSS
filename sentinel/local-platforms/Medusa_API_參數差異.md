# Medusa API 參數與實作差異

日期：2026-11-08。只新增核對紀錄，未修改 `Medusa_77_API_填寫參數.md`、既有 OpenAPI、採用清單、根目錄 compose 或既有服務／資料庫。

## 核對對象與證據層級

- 工作區應用與獨立測試映像：Medusa **2.22.4**、Node **22.22.0**，僅 `127.0.0.1:18084`。
- 工作區 bundled Store OpenAPI 的 `info.version` 是 **2.22.3**，選定清單 **79** 操作；舊文件 **77** 操作。不能把規格版本當成實際套件版本。
- 既有 `mirage-commerce-real-medusa-1` 另經唯讀套件查詢為 **2.21.0**，入口 9100。本次不修改它；這也不能補證歷史 8000 實例的版本或測試結果。
- 79 個操作均列於 [逐操作核對紀錄](Medusa_API_核對紀錄.md)，不是 79 個全部成功。舊參數尚未逐欄完整核實的部分保持未確認。
- 真實主流程證據：[第一次](reports/medusa-72caa767eed84dcead80c23929ac09b5.json)、[第二次](reports/medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json)。均建立實際新訂單，隨後以訂單 ID 與會員訂單清單重新核對。

## 已證實的輸入參數錯誤

| 操作／欄位 | 舊文件或 bundled 規格問題 | 固定版本的核對結果 |
|---|---|---|
| `POST /store/carts` → `shipping_address.id/created_at/updated_at` | 將地址回應模型欄位列為必要輸入 | 兩次實機僅送姓名、街道、城市、國家、郵遞區號、電話即成功；地址 ID 由伺服器產生。原生 Zod 驗證器拒絕上述三個額外欄位。 |
| 同操作 → `billing_address` | 也把完整地址模型當成請求模型 | 最小帳單地址成功建車、結帳與讀回訂單，沒有送地址 ID／時間。 |
| 同操作 → `items[].id` | 舊文件標示必要；bundled 規格引用完整品項回應模型 | 實機送 `{variant_id: 當次商品回應的變體ID, quantity: 1}` 即成功；不送 line-item ID。 |
| 同操作 → `items[].variant_id` | 舊文件標示非必要 | 原生 Zod 對只有 quantity 的品項回報缺少 `variant_id`；正常流程使用真實動態變體 ID。 |
| `POST /store/payment-collections/{id}/payment-sessions/{session_id}` | 現行新增操作不能沿用建立 session 的 `data` 形狀 | 實機送 `data` 回 400，指出必須提供 `client_data` 且 `data` 非法；改送 `client_data` 回 200。原生 `pp_system_default` 不保存／回傳該提供者特定資料，不能進一步宣稱已驗證第三方 PSP 的更新效果。 |
| `POST /store/search` | 舊 77 文件沒有此操作 | 固定版本接受 `entity: "product"`、`filters.q`、`pagination.take`；真實搜尋命中的 ID、標題與商品 API 回應相符，不只是回 200。 |

購物車的錯誤不只是舊文件過期：bundled 2.22.3 規格的 `StoreCreateCart` 也引用完整地址／品項回應 schema，未以 readOnly 正確排除回應專用欄位。因此不能只做「舊文件對 bundled 規格」比較就宣稱參數正確。

[原生驗證器探查](reports/medusa-cart-validator-probe.json) 的三個案例是直接呼叫固定套件的 Zod 驗證器，**不是 HTTP 業務測試**；其中測試識別字只用於 schema 檢查，從未作為成功下單證據。實機最小輸入的證據以兩份完整流程為準。錯誤 `data` 請求另保留 [400 紀錄](reports/medusa-d942b522823b49fab2ca49d6fcb508aa.json)。

## 規格列有而實作找不到的八個操作

[安裝套件與工作區編譯路由清單](reports/medusa-2.22.4-code-routes.json) 找不到下列 method/path；[實機探查](reports/medusa-probes-48d781ddfc6944bc9a3b5a8fe67eea31.json) 亦各回 404：

1. `POST /auth/customer/emailpass/verification/confirm`
2. `POST /store/carts/{id}/gift-cards`
3. `DELETE /store/carts/{id}/gift-cards`
4. `POST /store/carts/{id}/store-credits`
5. `GET /store/gift-cards/{idOrCode}`
6. `GET /store/store-credit-accounts`
7. `POST /store/store-credit-accounts/claim`
8. `GET /store/store-credit-accounts/{id}`

這是「目前固定套件與設定」的版本／功能差異，不能推論所有 Medusa 版本都沒有這些功能。購物車 ID 來自本次真實建車；禮卡與儲值明細的路由探查使用明確標示未發行的識別字，沒有假裝發行資產或驗證其業務。404 單獨不足以證明路由不存在，因此同時保留原始碼路由比對。不要使用這些探查作為 normal 訓練樣本。

## 前置條件與尚未解決的問題

- MFA：已在隔離 18084 實例的建置階段補入 `AUTH_MFA_ENCRYPTION_KEY`，並實機完成 TOTP 因子註冊、驗證、備援碼產生與停用；見 [證據](reports/medusa-mfa-cf90592d78914c559ef5c9e935125a1b.json)。`POST /auth/mfa/challenges/{id}/verify` 仍缺少正常登入流程產生的真實 challenge ID，因此沒有用虛假 ID 將拒絕回應當成成功。
- `POST /store/shipping-options/{id}/calculate`：對本次真實購物車與配送 ID 回 **500**。固定套件 `@medusajs/fulfillment-manual/dist/services/manual-fulfillment.js` 的 `canCalculate()` 回 false，`calculatePrice()` 明確拋出 `Manual fulfillment does not support price calculation`。須另配置支援計價的提供者才有正常情境；已通過的固定費率配送不需此操作。
- Payment session 更新：路由與 `client_data` 輸入已確認，但離線 system provider 無法驗證 PSP 特定資料保存，因此仍列前置條件不足。
- OAuth callback、重設密碼、一般 verification request/confirm 尚缺第三方提供者／郵件或驗證碼送達與讀回的完整情境；沒有送出真實外部郵件、扣款或杜撰 Token。
- 促銷新增／移除、四個訂單移轉操作、退貨申請共 7 個操作仍未完成正常實測。需有效促銷、移轉雙方與有效 token，退貨還需要已履約訂單；目前沒有可用的有效業務資產，不能把前置條件不足的拒絕回應算成確認。
- `GET /store/locales` 真實回傳空清單；只驗證清單路由，不代表翻譯內容或語系切換已完成。
- 測試映像只在**複製進映像的設定**加入 `admin.disable=true`，避免在有限記憶體編譯管理介面；來源 `backend/medusa-config.ts` 未改，未驗證管理介面／商店瀏覽器畫面。

## 可重現方式

依 [操作說明](README.md) 逐個啟動。`run_medusa.py` 是正常主流程；`probe_medusa.py` 是額外真實功能／路由探查，含預期不成功的請求，必須與正常資料分開。`run_medusa_mfa.py` 是 MFA 情境測試，現已完成 TOTP 因子與備援碼生命週期。所有憑證只留在 `.runtime` 或記憶體，公開結果遮蔽。

這些是環境／合約驗證，不使用 Medusa 訓練模型、選特徵或調門檻，也不代表未知攻擊偵測能力。

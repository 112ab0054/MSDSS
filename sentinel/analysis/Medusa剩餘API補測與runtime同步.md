# Medusa剩餘API補測與runtime同步

後續補證：密碼重設HTTP已確認產生新Token並使舊Token失效；搜尋可用GET /store/products?q=...；付款可透過建立API替換session（ID會改變）。原79操作分類仍為60／1／7／11，累計357筆HTTP與實際分數匹配、193項業務斷言通過。 [補證與替代API](Medusa剩餘項目再補證與替代API.md)。下列先前累計數字屬歷史輪次。

最新補資料實測：60成功、1部分成功、7前置不足、11版本／功能差異，not_run=0；339筆HTTP與實際gateway分數匹配，184項業務斷言通過。促銷、四種目錄明細、密碼更新、退貨及通用驗證碼已補通；通知／郵件送達仍未驗證。 [本輪實測紀錄](Medusa補測資料建立與驗收.md)。下列先前數字保留作歷史紀錄。


**最新依原文件復核：51成功、3部分成功、14前置不足、11版本／功能差異，not_run=0。Cookie兩項在真正HTTPS補測成功；移轉接受／拒絕也通過，通知送達未測；配送500已定位manual不支援動態計價，改列前置不足。** 詳見[原文件逐項復核](Medusa依原API文件逐項復核.md)。以下先前統計／未定位原因為歷史，原始HTTP失敗紀錄仍保留。

已修正上次只寫獨立報告、沒有更新選定清單的落差。原清單79項runtime_status都是not_run；本次全部逐項同步，not_run=0。

## 最新結果

| runtime_status | 意義 | 數量 |
| --- | --- | ---: |
| unavailable_feature | 版本／功能差異 | 11 |
| passed | 成功 | 47 |
| blocked_prerequisite | 前置條件不足 | 18 |
| partial_pass | 部分成功 | 2 |
| failed_runtime | 實測失敗 | 1 |

79項都有真實HTTP回應，含明確標示的缺參數／未發行ID負向探查；不是79個正常業務流程都成功。本輪補測107筆，加原正常流程58筆與Cookie／配送查詢覆核7筆，共172筆，都有實際gateway日誌UUID對應的分數，沒有用事後重算補造。82項已執行業務斷言通過。

目前目標仍是Sentinel http://127.0.0.1:18085 → 真實Medusa http://127.0.0.1:9100，應用2.21.0，模型仍Colab v9、權重未改。沒有重訓、調門檻、改根compose、重設資料庫、改MFA／通知／Cookie設定或變更Mirage。只在自己新建的測試帳號、購物車及訂單操作；沒有真實扣款。

## 狀態依據與限制

- 成功：HTTP及該操作業務斷言通過；不等於所有參數分支都測過。新增包含MFA因子清單、建立email驗證請求、購物車計稅、訂單移轉申請及取消。
- 部分成功：POST／DELETE促銷只測合法空promo_codes分支，查回同一購物車與空促銷清單；沒有有效折扣碼，不能說實際套用／移除折扣成功。
- 前置不足：MFA缺encryption key；通知未提供合法驗證／重設／移轉token；Cookie沒有建立；空目錄沒有明細ID；測試訂單尚未履約不能退貨。缺ID案例有清楚的msdss-probe-no-*標記，只是負向路由探查，絕不當真實ID或正常成功。
- 版本／功能差異：禮卡、儲值金、store/search、付款session更新及舊emailpass驗證確認等路由，安裝的原生2.21.0套件沒有對應方法且HTTP404。locales則不同：套件內有route，但目前服務404，未掛載／未啟用原因尚未定位，不把全部404都說成版本缺路由。
- 實測失敗：以真實cart_id與shipping option ID呼叫額外配送calculate回500；目前manual提供者，固定配送與結帳成功，但此計價操作根因尚待定位，不算通過。

## 重要發現

1. GET /store/return-reasons/{id}對未發行ID回200空物件，而非預期404；沒有return_reason實體，也沒有真實明細ID，所以列前置不足，未算成功。僅看HTTP200會得到錯結論。
2. POST /auth/session回200，但本次HTTP入口沒有Set-Cookie；Cookie metadata只記屬性、不記值，覆核為空陣列，移除Bearer後GET本人401，DELETE session也401。沒有假設一定是secure/domain造成，也沒有手工偽造Cookie補過。
3. POST /auth/mfa/factors實際400明確表示MFA encryption key is required to use MFA methods。沒有改既有服務金鑰設定；因子／挑戰／備援碼後續只做缺前置的負向探查，不捏造TOTP或factor ID當成功。
4. emailpass callback回401且明確說此provider未實作Callback authentication；缺第三方OAuth配置，不是一般emailpass登入不能用。
5. 對自己的測試email申請reset-password回201，只證明受理，不等於有通知送達及密碼重設完成；update使用一般登入JWT回401 Invalid token，不能自行簽發reset token繞過真實流程。
6. 通用email驗證request回201，已核對entity_id與code_provider；confirm缺合法code回400，兩項狀態分開。
7. 兩個自己的測試顧客完成移轉申請與取消HTTP200，並分別查兩者訂單清單確認owner未變；另唯讀SELECT自己的訂單order_change，確認transfer記錄存在且取消後deleted_at非空。原生cancel workflow是soft-delete，不是把status字面改成canceled；沒有寫資料庫或讀取transfer token。
8. 真實未履約訂單申請退貨回400，訊息表示退貨量超過fulfilled quantity；沒有為湊成功擅自履約或改後台資料。

## 逐項狀態

| 方法 | API | 狀態 | 說明 |
| --- | --- | --- | --- |
| POST | `/auth/customer/emailpass/verification/confirm` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |
| GET | `/auth/customer/providers` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/auth/customer/{auth_provider}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/auth/customer/{auth_provider}/callback` | 前置條件不足 | 目前只配置emailpass，沒有第三方OAuth提供者／授權回呼資料 |
| POST | `/auth/customer/{auth_provider}/register` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/auth/customer/{auth_provider}/reset-password` | 前置條件不足 | 對自己的測試帳號申請重設；201只表示受理，尚未取得通知送達的重設token |
| POST | `/auth/customer/{auth_provider}/update` | 前置條件不足 | 登入JWT不等於reset-password郵件token；缺少合法重設token，未捏造或自行簽發 |
| POST | `/auth/mfa/challenges/{id}/verify` | 前置條件不足 | MFA未完成註冊，沒有真實因子／挑戰／備援碼前置；只做路由與缺參數探查 |
| GET | `/auth/mfa/factors` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/auth/mfa/factors` | 前置條件不足 | MFA註冊失敗：MFA encryption key is required to use MFA methods |
| DELETE | `/auth/mfa/factors/{id}` | 前置條件不足 | MFA未完成註冊，沒有真實因子／挑戰／備援碼前置；只做路由與缺參數探查 |
| POST | `/auth/mfa/factors/{id}/verify` | 前置條件不足 | MFA未完成註冊，沒有真實因子／挑戰／備援碼前置；只做路由與缺參數探查 |
| POST | `/auth/mfa/recovery-codes` | 前置條件不足 | MFA未完成註冊，沒有真實因子／挑戰／備援碼前置；只做路由與缺參數探查 |
| POST | `/auth/session` | 前置條件不足 | 本機HTTP入口Cookie登入前置條件未滿足；後續明確使用Bearer，不能宣稱Cookie維持登入成功；POST session真實200，但回應未發出可供本機HTTP使用的Set-Cookie；移除Bearer後仍401，沒有改服務設定或手工偽造Cookie |
| DELETE | `/auth/session` | 前置條件不足 | 沒有有效Cookie session，刪除回未授權，不能列為登出成功；沒有可用Cookie session；不把DELETE回401當成登出成功 |
| POST | `/auth/token/refresh` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/auth/verification/confirm` | 前置條件不足 | 未配置驗證通知取碼途徑，沒有真實code；本次僅驗證缺參數會被拒絕 |
| POST | `/auth/verification/request` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/carts` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/carts/{id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/carts/{id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/carts/{id}/complete` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/carts/{id}/customer` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/carts/{id}/gift-cards` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |
| DELETE | `/store/carts/{id}/gift-cards` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |
| POST | `/store/carts/{id}/line-items` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/carts/{id}/line-items/{line_id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| DELETE | `/store/carts/{id}/line-items/{line_id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/carts/{id}/promotions` | 部分成功 | 合法空promo_codes分支已查回同一車與空促銷清單；沒有有效促銷碼，未驗證折扣套用／移除 |
| DELETE | `/store/carts/{id}/promotions` | 部分成功 | 合法空promo_codes分支已查回同一車與空促銷清單；沒有有效促銷碼，未驗證折扣套用／移除 |
| POST | `/store/carts/{id}/shipping-methods` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/carts/{id}/store-credits` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |
| POST | `/store/carts/{id}/taxes` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/collections` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/collections/{id}` | 前置條件不足 | 資料庫清單為空，沒有真實明細ID；此未發行識別值只做404負向路由探查，不能當正常流程 |
| GET | `/store/currencies` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/currencies/{code}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/customers` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/customers/me` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/customers/me` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/customers/me/addresses` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/customers/me/addresses` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/customers/me/addresses/{address_id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/customers/me/addresses/{address_id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| DELETE | `/store/customers/me/addresses/{address_id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/gift-cards/{idOrCode}` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |
| GET | `/store/locales` | 版本／功能差異 | 安裝套件有路由但展示站實際404，功能未掛載／啟用原因尚未定位，不能只歸因版本 |
| GET | `/store/orders` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/orders/{id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/orders/{id}/transfer/accept` | 前置條件不足 | 沒有送達的合法transfer token；只測缺少token會被拒絕，不自行簽發或偽造 |
| POST | `/store/orders/{id}/transfer/cancel` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/orders/{id}/transfer/decline` | 前置條件不足 | 沒有送達的合法transfer token；只測缺少token會被拒絕，不自行簽發或偽造 |
| POST | `/store/orders/{id}/transfer/request` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/payment-collections` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/payment-collections/{id}/payment-sessions` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/payment-collections/{id}/payment-sessions/{session_id}` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |
| GET | `/store/payment-providers` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/product-categories` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/product-categories/{id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/product-options` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/product-options/{id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/product-tags` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/product-tags/{id}` | 前置條件不足 | 資料庫清單為空，沒有真實明細ID；此未發行識別值只做404負向路由探查，不能當正常流程 |
| GET | `/store/product-types` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/product-types/{id}` | 前置條件不足 | 資料庫清單為空，沒有真實明細ID；此未發行識別值只做404負向路由探查，不能當正常流程 |
| GET | `/store/product-variants` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/products` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/products/{id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/regions` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/regions/{id}` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/return-reasons` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| GET | `/store/return-reasons/{id}` | 前置條件不足 | 資料庫清單為空，沒有真實明細ID；此未發行識別值只做404負向路由探查，不能當正常流程 |
| POST | `/store/returns` | 前置條件不足 | 本次測試訂單尚未履約／缺退貨配送條件，回應為前置拒絕；未修改後台履約或假裝退貨成功 |
| POST | `/store/search` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |
| GET | `/store/shipping-options` | 成功 | 真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過 |
| POST | `/store/shipping-options/{id}/calculate` | 實測失敗 | 使用真實車與配送ID計價回500；目前manual提供者，根因仍待定位，不算通過 |
| GET | `/store/store-credit-accounts` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |
| POST | `/store/store-credit-accounts/claim` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |
| GET | `/store/store-credit-accounts/{id}` | 版本／功能差異 | 本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功 |

## 同步位置與重跑

- 主要清單：sentinel/analysis/api-extension/medusa-holdout-inventory.json。每項包含runtime_status、reason、HTTP狀態、實測request IDs、證據檔、是否僅負向探查及實際版本。原79個方法／路徑及規格application_version未改，最新實機版本另放runtime_application_version／runtime_verification，避免把2.21.0當2.22.4。
- 完整機器報告：sentinel/local-platforms/reports/medusa-demo-v9-runtime-status.json。
- 可閱讀CSV：medusa-demo-v9-api-status.csv；分數表：medusa-demo-v9-all-runtime-predictions.csv。
- 原42成功／29未測表是第一輪快照；當前summary與CSV已更新。其他舊的18084獨立2.22.4報告保留歷史，不拿來冒充這次9100展示站實測。

```powershell
python -X utf8 -B sentinel/local-platforms/run_medusa_remaining.py
python -X utf8 -B sentinel/local-platforms/audit_medusa_runtime.py --sync-inventory
```

第一行會重新建立自己的測試帳號／訂單並送真實API，使用私有.runtime/medusa-demo.json。重新執行前，須讓自己的gateway將日誌保存至私有檔案（例如啟動命令後加 `2> sentinel/local-platforms/.runtime/medusa-gateway.log`，不要同時啟動兩個佔用18085的程序）。HTTP完成後先執行下面的日誌匯入，再執行audit同步。缺少同輪UUID分數會拒絕，不以重算或舊分數補值。

```powershell
python -X utf8 -B sentinel/local-platforms/import_gateway_scores.py --log sentinel/local-platforms/.runtime/medusa-gateway.log --evidence sentinel/local-platforms/reports/medusa-demo-v9-remaining.json --output sentinel/local-platforms/reports/medusa-demo-v9-remaining-gateway-scores.json
python -X utf8 -B sentinel/local-platforms/audit_medusa_runtime.py --sync-inventory
```

證據JSON指紋使用解析後JSON、排序鍵、UTF-8，避免Git只改外層換行就失配；內嵌raw body/query、空白、大小寫與編碼完全保留，沒有正規化模型輸入。


驗證完成：5項runtime／日誌匯入測試與16項gateway測試通過；79方法／路徑順序及原規格版本、來源SHA、角色未改。主要manifest沒有任何runtime_status=not_run，證據JSON指紋重算一致。原模型及訓練資料完全未改。

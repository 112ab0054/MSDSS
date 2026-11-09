# Medusa依原API文件逐項復核32項

本次不是只重貼上一輪分類：以使用者原手寫文件、bundled Store規格、目前安裝2.21.0程式碼、安全設定、資料庫唯讀觀察及補測回應交叉確認，並修正先前不夠精確的測試條件與判定。

## 文件來源與保留

原檔是C:/Users/USER/Downloads/MSDSS/Medusa_77_API_填寫參數.md；目前GitHub工作副本缺這份檔案。已新增[原文逐位元快照](history/2026-11-09/medusa-77-user-reference.md)，不改任何標題、參數、說明或範例。原件及快照SHA256：`5da9819f744aae3f04ddefa283bf464f84c05972444ed431b104b7b617d44031`。Git針對此快照保留原始bytes。

32項以提交6c2454f中非passed操作固定選取，不因本次轉成功就從復核表刪除。原文件解析為77操作；其中payment-session更新與store/search是新79清單才有的兩項，沒有假稱在原77文件找到了它們。這兩項另對bundled2.22.3規格。

## 最新整體狀態

| 狀態 | 數量 |
| --- | ---: |
| 版本／功能差異 | 11 |
| 成功 | 51 |
| 前置條件不足 | 14 |
| 部分成功 | 3 |

79項都有HTTP紀錄，not_run=0；合計251筆HTTP與實際gateway分數逐UUID匹配，129項已執行業務斷言通過。仍含負向探查，不是79個正常業務流程都通過。模型、特徵及訓練資料未改。

## 已修正或釐清的判定

### Cookie兩項已在正確HTTPS條件下通過

原手寫文件要求POST帶登入JWT、DELETE帶connect.sid；原HTTP測試未能建立Cookie。實際production設定及framework express-loader確認Secure=true、SameSite=lax，且沒有覆寫。這不應直接說API不可用。

已另外啟動僅本機https://127.0.0.1:18443入口，由真實ASGI TLS scheme產生X-Forwarded-Proto，會移除客戶端假傳的該標頭。客戶端以私有本機憑證驗證TLS（沒有關閉驗證），CookieJar自然取得Secure Cookie，移除Bearer仍能讀回同一顧客，DELETE後Cookie清除且再查401。沒有手工塞假Cookie，也沒有改既有Medusa設定。

**成功範圍是HTTPS，原http://127.0.0.1:18085不能因此說Cookie也成功。** HTTPS入口仍連同一個9100真實Medusa，不是另一套假回應。私有TLS憑證只供本機測試，與MFA encryption key是不同用途，沒有安裝系統信任或修改MFA設定。

### 接受／拒絕訂單移轉兩項已通過

按文件帶真實order ID及平台生成token。本輪自己建立訂單與接收者帳號，先POST transfer/request，由Medusa原生流程在order_change_action.details產生UUID token。測試工具只用唯讀SELECT取這筆自己訂單／自己接收者的原生值，沒有自行簽發或杜撰。token不存公開紀錄、不進訓練。

decline後：變更為declined，原owner仍有訂單、接收者沒有。另一次原生request後accept：變更為confirmed，原owner清單不再有該訂單，接收者清單包含它。API本身、token驗證及歸屬變更都是真實平台結果。**這個測試取碼管道是本機唯讀觀察，通知／郵件送達仍未驗證，不能把整個寄信流程也說通過。**

### 配送500已定位為提供者不支援，不再列不明失敗

文件Body cart_id必填、data選填；原請求已有真實cart ID與option ID，沒有缺必填cart_id。當次選項是manual_manual、price_type=flat。安裝的@medusajs/fulfillment-manual實作canCalculate()回false，calculatePrice()直接拋出Manual fulfillment does not support price calculation。

因此HTTP500原始證據保留，分類改為「前置條件不足：需要支援動態計價的提供者」，不是偷偷改成200或成功，也不是隨便補data就能修好。固定費率配送與結帳已通過，與額外calculate功能分開。

### locales是已停用功能，不是2.21沒有這個API

原生route標示自2.12.3存在，並由translation feature flag控制。實際解析設定translation模組disable=true，與404一致。先前「原因未定位」已釐清，仍列版本／功能差異，但精確原因是目前功能被停用；沒有改設定強行通過。

### 重設請求與密碼更新分開判斷

原文件reset-password用途是要求產生token並發auth.password_reset事件，本身不承諾郵件送達。本次對確實存在且已登入驗證過的自己帳號送正確identifier，回201。但此路由刻意不暴露帳號／workflow錯誤，且未取得事件的獨立觀測，因此列「部分成功：請求受理」，不把缺寄信當成參數錯，也不宣稱token事件或完整重設成功。

update則不同：文件明確要求Authorization為重設token，並列email與password。之前負向探查只送password；本次補齊email＋password，用已證明有效的一般登入JWT仍401 Invalid token。關鍵是缺合法重設token，不能把登入JWT當成重設token，這個操作仍前置不足。

## 其他前置條件已核實

- MFA：原註冊provider=totp與登入資料正確；回應明確說缺MFA encryption key，實際設定也確認未配置。沒有真實因子／挑戰就不能測成功驗證、停用與備援碼，缺code紀錄只算負向探查。
- OAuth callback：文件用途是第三方登入；雖然共用Path欄有emailpass例子，不能推定emailpass實作callback。目前只配emailpass，原生回應明確Callback authentication not implemented。
- 通知／取碼：目前只有local通知提供者的feed channel，沒有email channel，src/subscribers為空。文件提到事件不表示目前已配置通知送達，不能杜撰code或重設token。
- 優惠碼兩項：promo_codes=[]只是清除／空操作合法分支。唯讀DB promotion=0，沒有有效碼可真實套用／移除，所以仍部分成功。
- 四個目錄明細：product_collection、product_tag、product_type、return_reason的未刪除列都是0；沒有真實ID。return-reasons未發行ID甚至200空物件，仍不能算明細成功。
- 退貨：文件必填物件已送，但自己的測試品項fulfilled_quantity=0，原生拒絕超過履約數量；退貨配送查詢原本漏cart_id，已補cart_id＋is_return=true回200空清單。仍缺已履約品項與可用退貨配送，沒有修改後台履約湊成功。
- 10個原生未提供路由：以安裝包方法／路徑與HTTP404雙重確認，不把空body拒絕假稱正常驗收。涉及真實禮卡／儲值碼但尚未發行時，未用任意字串冒充。2.22.4獨立環境的歷史成功不混算到目前2.21.0。

## 原32項逐項對照

每項完整文件參數、必填／選填說明、抽樣請求欄位是否存在、正負向性與證據ID均在[JSON](../local-platforms/reports/medusa-demo-v9-user-document-audit.json)，方便閱讀版在[CSV](../local-platforms/reports/medusa-demo-v9-user-document-audit.csv)。欄位存在不代表資源ID／token合法，兩者刻意分開。

| 方法／API | 文件章節／行 | 舊狀態 → 本次 | 確認結果 |
| --- | --- | --- | --- |
| POST `/auth/customer/emailpass/verification/confirm` | 01. 確認電子郵件驗證／7 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |
| POST `/auth/customer/{auth_provider}/callback` | 04. 完成第三方登入回呼驗證／42 | blocked_prerequisite → blocked_prerequisite | 文件用途是第三方回呼；auth_provider欄位例emailpass不能當作該provider支援callback。現只配置emailpass，原生回應明確未實作callback。 |
| POST `/auth/customer/{auth_provider}/reset-password` | 06. 要求產生重設密碼 token／66 | blocked_prerequisite → partial_pass | 文件此操作是要求產生token並發事件，不是寄信本身。已依identifier呼叫201；因回應故意不透露帳號是否存在、尚無事件獨立證據，列部分成功，不能說缺郵件就是參數錯。 |
| POST `/auth/customer/{auth_provider}/update` | 07. 使用 token 重設密碼／79 | blocked_prerequisite → blocked_prerequisite | 文件明確要求重設密碼token。上次僅password且用了普通登入JWT；本次補email＋password仍401。缺合法reset token是關鍵，不把登入JWT冒充重設JWT。 |
| POST `/auth/mfa/challenges/{id}/verify` | 08. 驗證登入時的 MFA 挑戰／93 | blocked_prerequisite → blocked_prerequisite | 依文件註冊先送provider=totp、已登入。原生400與安全設定均確認缺MFA encryption key，故無真實factor／challenge／recovery code。後續未填code的紀錄只是負向探查。 |
| POST `/auth/mfa/factors` | 10. 開始綁定 MFA 因子／116 | blocked_prerequisite → blocked_prerequisite | 依文件註冊先送provider=totp、已登入。原生400與安全設定均確認缺MFA encryption key，故無真實factor／challenge／recovery code。後續未填code的紀錄只是負向探查。 |
| DELETE `/auth/mfa/factors/{id}` | 11. 停用 MFA 因子／131 | blocked_prerequisite → blocked_prerequisite | 依文件註冊先送provider=totp、已登入。原生400與安全設定均確認缺MFA encryption key，故無真實factor／challenge／recovery code。後續未填code的紀錄只是負向探查。 |
| POST `/auth/mfa/factors/{id}/verify` | 12. 確認並啟用 MFA 因子／145 | blocked_prerequisite → blocked_prerequisite | 依文件註冊先送provider=totp、已登入。原生400與安全設定均確認缺MFA encryption key，故無真實factor／challenge／recovery code。後續未填code的紀錄只是負向探查。 |
| POST `/auth/mfa/recovery-codes` | 13. 重新產生 MFA 恢復碼／158 | blocked_prerequisite → blocked_prerequisite | 依文件註冊先送provider=totp、已登入。原生400與安全設定均確認缺MFA encryption key，故無真實factor／challenge／recovery code。後續未填code的紀錄只是負向探查。 |
| POST `/auth/session` | 14. 建立 Cookie 登入工作階段／170 | blocked_prerequisite → passed | 手寫文件的JWT／connect.sid用法正確；HTTP不符production Secure Cookie。真正HTTPS、驗證憑證、CookieJar自動維持與刪除身分均已補測成功。 |
| DELETE `/auth/session` | 15. 結束 Cookie 登入工作階段／180 | blocked_prerequisite → passed | 手寫文件的JWT／connect.sid用法正確；HTTP不符production Secure Cookie。真正HTTPS、驗證憑證、CookieJar自動維持與刪除身分均已補測成功。 |
| POST `/auth/verification/confirm` | 17. 確認通用驗證碼／200 | blocked_prerequisite → blocked_prerequisite | 文件必填code，實際沒有通知接收途徑取得原生code；先前省略code的400不是正向驗收。現只有feed通知、src/subscribers空，未配置email發送／取碼。 |
| POST `/store/carts/{id}/gift-cards` | 24. 套用禮物卡／353 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |
| DELETE `/store/carts/{id}/gift-cards` | 25. 移除禮物卡／368 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |
| POST `/store/carts/{id}/promotions` | 29. 套用優惠碼／436 | partial_pass → partial_pass | 文件用途是套用／移除優惠碼，空陣列只覆蓋清除分支。唯讀DB promotion=0，不能把任意字串當成真優惠碼；兩項保留部分成功。 |
| DELETE `/store/carts/{id}/promotions` | 30. 移除優惠碼／452 | partial_pass → partial_pass | 文件用途是套用／移除優惠碼，空陣列只覆蓋清除分支。唯讀DB promotion=0，不能把任意字串當成真優惠碼；兩項保留部分成功。 |
| POST `/store/carts/{id}/store-credits` | 32. 使用商店抵用額度／487 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |
| GET `/store/collections/{id}` | 35. 取得單一商品集合／542 | blocked_prerequisite → blocked_prerequisite | 文件要求既有資源ID，唯讀資料庫對應表皆0筆；未發行ID只是負向探查。return-reasons甚至200空物件，不能當成功。 |
| GET `/store/gift-cards/{idOrCode}` | 46. 查詢禮物卡／759 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |
| GET `/store/locales` | 47. 列出支援語系／773 | unavailable_feature → unavailable_feature | 不是缺路由：原生標示自2.12.3存在、以translation feature flag控制；實際translation module disable=true。屬目前功能設定，不是必須升級或補locale參數。 |
| POST `/store/orders/{id}/transfer/accept` | 50. 接受訂單歸戶轉移／823 | blocked_prerequisite → passed | 依文件送本次真實訂單ID與平台產生的token後已成功，接受／拒絕後查雙方訂單歸屬及confirmed／declined狀態。token唯讀取自己訂單資料列，沒有偽造；郵件送達未驗證。 |
| POST `/store/orders/{id}/transfer/decline` | 52. 拒絕訂單歸戶轉移／854 | blocked_prerequisite → passed | 依文件送本次真實訂單ID與平台產生的token後已成功，接受／拒絕後查雙方訂單歸屬及confirmed／declined狀態。token唯讀取自己訂單資料列，沒有偽造；郵件送達未驗證。 |
| POST `/store/payment-collections/{id}/payment-sessions/{session_id}` | 原77文件未列，另對新規格 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |
| GET `/store/product-tags/{id}` | 62. 取得單一商品標籤／1049 | blocked_prerequisite → blocked_prerequisite | 文件要求既有資源ID，唯讀資料庫對應表皆0筆；未發行ID只是負向探查。return-reasons甚至200空物件，不能當成功。 |
| GET `/store/product-types/{id}` | 64. 取得單一商品類型／1088 | blocked_prerequisite → blocked_prerequisite | 文件要求既有資源ID，唯讀資料庫對應表皆0筆；未發行ID只是負向探查。return-reasons甚至200空物件，不能當成功。 |
| GET `/store/return-reasons/{id}` | 71. 取得單一退貨原因／1241 | blocked_prerequisite → blocked_prerequisite | 文件要求既有資源ID，唯讀資料庫對應表皆0筆；未發行ID只是負向探查。return-reasons甚至200空物件，不能當成功。 |
| POST `/store/returns` | 72. 建立退貨要求／1255 | blocked_prerequisite → blocked_prerequisite | 文件必填order_id、items.id／quantity、return_shipping.option_id有送；實例fulfilled_quantity=0且沒有可用退貨配送選項。原生400證明業務前置不足，不是任填品項ID可解決。 |
| POST `/store/search` | 原77文件未列，另對新規格 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |
| POST `/store/shipping-options/{id}/calculate` | 74. 計算配送選項價格／1300 | failed_runtime → blocked_prerequisite | 文件cart_id必填、data選填，先前已有真實cart／option ID。實際provider=manual_manual、price_type=flat；原生canCalculate=false且calculatePrice明確拋錯。500保留，改列需支援動態計價provider的前置不足。 |
| GET `/store/store-credit-accounts` | 75. 列出自己的商店額度帳戶／1317 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |
| POST `/store/store-credit-accounts/claim` | 76. 認領商店額度帳戶／1340 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |
| GET `/store/store-credit-accounts/{id}` | 77. 取得自己的額度帳戶／1355 | unavailable_feature → unavailable_feature | 文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。 |

## 重跑方式與證據

既有HTTP入口保留，Cookie驗證另用真正HTTPS；不要同時啟動兩個佔用同一埠的程序。憑證只有兩天效期，過期需自行保留舊檔另行換新；工具不覆寫既有憑證。

```powershell
python -X utf8 -B sentinel/local-platforms/prepare_medusa_tls.py
$env:MEDUSA_UPSTREAM='http://127.0.0.1:9100'
python -m uvicorn tls_demo_gateway:app --app-dir sentinel/local-platforms --host 127.0.0.1 --port 18443 --ssl-keyfile sentinel/local-platforms/.runtime/medusa-document-check-tls.key --ssl-certfile sentinel/local-platforms/.runtime/medusa-document-check-tls.crt --no-access-log
```

另一視窗依序可跑：

```powershell
python -X utf8 -B sentinel/local-platforms/inspect_medusa_document_environment.py
python -X utf8 -B sentinel/local-platforms/run_medusa_document_checks.py
python -X utf8 -B sentinel/local-platforms/run_medusa_native_transfer_tokens.py
```

取碼程式只能用自己本輪新建資源，DB執行BEGIN READ ONLY／SELECT／ROLLBACK；所有狀態變動經真實HTTP，沒有SQL寫入。這些流程會新增測試帳號、購物車與未真實扣款訂單。密碼、token、Cookie、金鑰只在記憶體／私有.runtime，不寫公開紀錄。

需要同步狀態時，先用import_gateway_scores.py將該輪實際gateway日誌依UUID匯入，再執行audit_medusa_runtime.py --sync-inventory與reconcile_medusa_user_document.py。缺分數不重算補造；原文件snapshot、方法／路徑、規格來源SHA及模型權重保持原樣。


驗證結果：16項本機證據／runtime／文件對照測試及16項gateway測試通過。32項固定復核集合、原文件77操作與原件SHA、251筆HTTP對應實際分數均已核對。既有79方法／路徑、根compose、原Medusa設定、原API原件及模型權重未改；私有TLS key／CA檔仍僅留.runtime。

公開前另以本輪平台原生transfer token的真值及商店金鑰逐檔掃描Git提交內容，確認沒有洩漏；TLS私鑰／憑證均未納入。原77文件的Git暫存bytes與Downloads原件完全一致，跨Git外層換行後的證據指紋仍匹配。

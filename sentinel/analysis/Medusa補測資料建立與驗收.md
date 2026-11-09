# Medusa 補齊測試資料後的實測結果

2026-11-09，依使用者指示，實際建立缺少的本機測試資料，繼續驗證原本未完成的 API。對象仍是 127.0.0.1:9100 的真實 Medusa 2.21.0，未改現有服務設定、資料庫結構、根 compose、Mirage、模型或訓練資料。測試資料透過已安裝平台的原生服務／workflow 建立，沒有直接寫 SQL，也沒有用假回應。

| 狀態 | 補資料前 | 本輪後 |
| --- | ---: | ---: |
| 成功 | 51 | 60 |
| 部分成功 | 3 | 1 |
| 前置條件不足 | 14 | 7 |
| 版本／功能差異 | 11 | 11 |
| 尚未測試 | 0 | 0 |

本輪新增 88 筆真實 HTTP，55 項業務斷言通過。每筆均以 UUID 對上 gateway 實際輸出的三類分數。累計 339 筆 HTTP、184 項業務斷言通過、0 項斷言失敗。這些含刻意測試舊密碼或重用驗證碼被拒絕的負向對照，不是 339 筆都應成功，也不是模型準確率。

## 新增通過的 9 個操作

| API | 怎麼補條件、怎麼確認 |
| --- | --- |
| POST /store/carts/{id}/promotions | 原生建立 active、非自動、商品金額 10% 折扣碼。購物車原總額 20，套用後折扣 2、總額 18；另 GET 同車確認優惠碼及金額，不只看200。 |
| DELETE /store/carts/{id}/promotions | 移除剛套用的同一有效碼；再 GET 確認該碼不存在、折扣0、總額恢復20。 |
| GET /store/collections/{id} | 原生建立帶MSDSS標記的集合，實際讀回相同ID與title。 |
| GET /store/product-tags/{id} | 原生建立測試標籤，實際讀回相同ID與value。 |
| GET /store/product-types/{id} | 原生建立測試商品類型，實際讀回相同ID與value。 |
| GET /store/return-reasons/{id} | 原生建立測試退貨原因，實際讀回相同ID與value，排除先前200空物件的情況。 |
| POST /auth/customer/{auth_provider}/update | 自己新建帳號，由平台原生generateResetPasswordTokenWorkflow產生reset JWT；HTTP更新後，舊密碼401、新密碼200登入並讀回同一顧客。沒有手動簽JWT。 |
| POST /store/returns | 先用真實購物流程建立自己的新訂單，再用原生createOrderFulfillmentWorkflow履約一件，HTTP確認fulfilled_quantity至少1。建立獨立manual固定費率退貨配送並查回；POST退貨成功，status=requested，品項及數量正確，再GET訂單確認return_requested_quantity=1。 |
| POST /auth/verification/confirm | 自己新帳號先HTTP要求驗證；原生Auth服務產生真實code，再HTTP確認entity_id、entity_type、code_provider及verified_at。重用同碼被拒絕，沒有杜撰code。 |

**取碼與寄信分開：** reset JWT及通用驗證碼由本機測試工具取得平台原生功能的輸出，完整值只保存在ignored .runtime或記憶體；公開請求證據遮蔽。這能驗證持有有效碼時的更新／確認API，不代表收信或通知送達已成功。HTTP reset-password要求本身仍列部分成功，沒有拿另一個原生workflow的結果冒充該HTTP事件已被觀測。

**退貨範圍：** 只對本輪新訂單履約與建立退貨要求，沒有對舊訂單或其他使用者訂單操作。manual提供者為離線測試，沒有真實寄件、外部運費服務、真實扣款或退款。退貨狀態是requested，不宣稱倉庫已收到或已退款。

## 剩下 18 項為何仍未成功

- 部分成功1：POST reset-password，正確identifier回201，但平台刻意不透露帳號／流程錯誤，尚無該HTTP呼叫所發事件的獨立觀測；也未配置郵件接收。
- 前置不足5：MFA註冊、啟用、挑戰驗證、刪除因子、重生恢復碼。現有服務缺MFA encryption key；不是新增商品資料可解決。未修改現有認證設定。
- 前置不足1：第三方callback，目前僅emailpass，沒有OAuth提供者及第三方應用憑證，不能杜撰callback成功。
- 前置不足1：動態配送計價，目前manual_manual原生canCalculate=false、calculatePrice明確拋錯；新增flat退貨配送不會使動態計價變可用，既有500證據保留。
- 功能／版本差異11：locales目前translation模組停用；其他10項是目前2.21.0原生路由與HTTP404都確認未提供的方法／路徑（含禮物卡、商店額度、搜尋及付款session更新）。新增假資源不會補出不存在的路由，未修改平台版本或功能設定。

以上都保留未完成狀態，沒有為了變綠而停用檢查或修改回應。各API的實際狀態、理由與證據ID見[清單](../local-platforms/reports/medusa-demo-v9-api-status.csv)及[JSON](../local-platforms/reports/medusa-demo-v9-runtime-status.json)。

## 重跑與停止

原有18085／18443入口保留；本輪完成後已停止額外18444入口以釋放記憶體，重跑時依下列方式啟動。本輪另用僅綁127.0.0.1的18444 HTTPS入口，連同一個9100 Medusa。需使用已安裝gateway依賴的Python環境，私有publishable key已在.runtime/medusa-demo.json；不放入指令或文件。憑證由prepare_medusa_tls.py建立、客戶端明確信任並驗證，沒有關閉TLS驗證；既有兩天效期憑證過期時須換新。

從專案根目錄執行，先在獨立終端機啟動入口（若18444已在運作就直接使用，不要重複啟動）：

```powershell
python -X utf8 -B sentinel/local-platforms/start_medusa_fixture_gateway.py
```

在另一終端機依序建立／補測、整理狀態：

```powershell
python -X utf8 -B sentinel/local-platforms/medusa_native_fixture_runner.py
python -X utf8 -B sentinel/local-platforms/run_medusa_fixture_checks.py
python -X utf8 -B sentinel/local-platforms/run_medusa_verification_fixture.py
python -X utf8 -B sentinel/local-platforms/collect_medusa_fixture_scores.py
python -X utf8 -B sentinel/local-platforms/audit_medusa_runtime.py --sync-inventory
python -X utf8 -B sentinel/local-platforms/reconcile_medusa_user_document.py
```

啟動入口的終端機按Ctrl+C，只停止這個獨立入口，不停止Medusa或其他服務。每次重跑建立新的MSDSS測試資料、帳號、購物車及訂單，不自動刪除其他資料。latest報告會更新；需要保留某次執行，先另存reports副本。請勿平行執行同一套補測工具。

## 證據檔

- [建立的促銷及目錄ID](../local-platforms/reports/medusa-demo-v9-created-fixtures.json)
- [原生前置條件安全摘要](../local-platforms/reports/medusa-demo-v9-native-fixture-provenance.json)：不含JWT、code或密碼。
- [82筆HTTP與52項斷言](../local-platforms/reports/medusa-demo-v9-fixture-checks.json)
- [驗證碼6筆HTTP與3項斷言](../local-platforms/reports/medusa-demo-v9-verification-fixture-checks.json)
- [88筆實際gateway分數](../local-platforms/reports/medusa-demo-v9-fixture-gateway-scores.json)
- [原32項文件對照最新結果](../local-platforms/reports/medusa-demo-v9-user-document-audit.csv)

原始77操作API文件快照不變。模型SHA仍為e612214de592b01ec931cc73a100603928c89e747c61eebf3027424669f24993；未重訓、未把Medusa資料加入訓練。

本輪工具驗證：8項HTTP證據測試及10項runtime／文件／業務證據測試通過，Python語法與原生JS語法檢查通過；公開檔案未包含實際測試Token／code／publishable key，.runtime維持忽略。證據JSON的可攜指紋核對通過。

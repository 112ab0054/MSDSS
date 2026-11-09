# Medusa 剩餘項目再補證與可用替代 API

2026-11-09，本輪依「可以就繼續測」指示，沒有刪除API，繼續對同一個真實Medusa2.21.0執行。既有服務設定、認證設定、資料庫結構、Mirage、模型及訓練資料未改。只操作自己新建的測試帳號與購物車，資料庫觀察全部BEGIN READ ONLY／ROLLBACK。

## 密碼重設：已證實產生Token，不再只有201證據

1. 新建自己的測試帳號，登入並GET確認同一顧客。
2. 先由平台原生workflow產生一個有效reset JWT，完整值只留記憶體／ignored .runtime。
3. HTTP POST /auth/customer/emailpass/reset-password，identifier為該帳號。
4. 唯讀查到原生auth_password_reset_token資料列已換成新的ID，舊列不再有效。
5. 拿步驟2的舊JWT嘗試HTTP更新密碼，確實401。原密碼仍能登入，沒有被這次拒絕操作改掉。
6. 再次HTTP要求重設，確認再次換新且僅保留一筆有效Token資料列。
7. 對本輪隨機、未註冊的example.test帳號要求重設，也回201，但資料庫沒有Token資料列。這證明不能單獨以201判成功。

以上10筆HTTP、6項業務斷言通過，[HTTP證據](../local-platforms/reports/medusa-demo-v9-reset-state-checks.json)、[唯讀狀態證據](../local-platforms/reports/medusa-demo-v9-reset-state-proof.json)。不公開JWT、Token hash或密碼。

仍列部分成功1項：目前沒有該HTTP所發事件的獨立消費觀測，也沒有郵件送達證據。沒有使用另一個程序產生的JWT冒充本次HTTP的Token。

事件log的缺席也已釐清：安裝的event-bus-local只在有訂閱者時輸出Processing日誌；沒有那行log不能推定平台未發事件。workflow_execution中也沒有這個短工作流程的持久化執行證據。本輪不透過修改既有服務或加入訂閱者來強行取得事件。[原始碼指紋與條件](../local-platforms/reports/medusa-demo-v9-followup-source-proof.json)。

## 搜尋：確定能用的方式與另一路由的阻礙

| 方法／路徑 | 實測結論 |
| --- | --- |
| POST /store/search | 原79清單的舊路由，目前版本沒有，保留功能／版本差異。 |
| GET /store/products/search?q=商品名稱 | 安裝套件確實有GET路由，但實測404明確回No search index registered for product，Registered indexes: (none)。不是單純缺商品資料，也不是應把POST直接改成GET就能使用。 |
| GET /store/products?q=商品名稱 | 已實測可用。從商品清單取得真實名稱，再搜尋並查回同一ID；隨機不存在名稱回空清單，確認q確實有作用。 |

建議現有展示使用GET /store/products的q參數。這項本來就在已成功60個API中，不重複算成新的成功API。獨立products/search若要啟用，需要配置搜尋模組／商品索引，修改文件文字無法補出索引。

[4筆補充相容性HTTP](../local-platforms/reports/medusa-demo-v9-search-alternatives.json)獨立保存，未混入原79操作的統計。products/search不在原gateway偵測清單，沒有假稱它有模型分數。

## 付款session：可以替換，但不是更新原ID

舊清單的POST /store/payment-collections/{id}/payment-sessions/{session_id}仍未提供。實測可用的是已存在的POST /store/payment-collections/{id}/payment-sessions，Body為provider_id與data。

本輪新建自己的購物車、商品及付款集合，只用pp_system_default離線測試提供者：

- 第一次POST帶第一個msdss_demo_marker，查到一個pending session，data符合。
- 同一集合再次POST帶第二個marker，查到一個新的pending session，data為第二值；原session ID已換掉。
- GET購物車確認仍連同一集合，狀態not_paid；captured_amount／authorized_amount為平台尚未初始化的null或0。沒有授權、capture、下單或真實扣款。

因此可在展示中使用「重新建立付款session並採用回應的新ID」，不能文件寫成「更新原session ID」。這也是已成功清單內原有API的另一個參數分支，不增加成功數。[8筆HTTP](../local-platforms/reports/medusa-demo-v9-payment-alternative.json)、[替換結果](../local-platforms/reports/medusa-demo-v9-payment-alternative-proof.json)。

工具第一次把原生null金額直接轉float，發生本機TypeError，並非平台HTTP失敗。初次8筆診斷保留於ignored .runtime/payment-alternative-initial-null.json；修正為檢查not_paid及null／0的實際語意後，重新完整執行8筆通過。初次診斷不混算正式統計。

## 最新統計與仍有的限制

原79操作仍為60成功、1部分成功、7前置不足、11功能／版本差異；not_run=0。不是這輪沒有測，而是新增證據與替代做法不等於原本缺少的路由已存在。本輪正式納入18筆HTTP、9項斷言；累計357筆HTTP與實際gateway分數逐UUID匹配、193項業務斷言通過。另有4筆搜尋相容性探查、2項斷言獨立保存。

其他剩餘項目若要突破：MFA需加密設定，OAuth需第三方提供者與應用憑證，動態運費需支援計價外掛，locales需啟用翻譯功能，缺路由的禮卡／購物金等需實作或不同平台版本。這些都不能靠捏造ID、改參數名稱或只增加資料解決。目前遵守不修改既有Medusa服務的限制，未對它做上述設定變動。

## 重跑

使用已安裝gateway依賴的Python環境、有效的私有本機TLS憑證與.runtime/medusa-demo.json。先在獨立終端機執行start_medusa_fixture_gateway.py啟動127.0.0.1:18444；不重複佔用埠。另一個終端機依序：

```powershell
python -X utf8 -B sentinel/local-platforms/run_medusa_reset_state_checks.py
python -X utf8 -B sentinel/local-platforms/run_medusa_search_alternatives.py
python -X utf8 -B sentinel/local-platforms/run_medusa_payment_alternative.py
python -X utf8 -B sentinel/local-platforms/inspect_medusa_followup_sources.py
python -X utf8 -B sentinel/local-platforms/import_gateway_scores.py --log sentinel/local-platforms/.runtime/fixture-gateway.log --evidence sentinel/local-platforms/reports/medusa-demo-v9-reset-state-checks.json --output sentinel/local-platforms/reports/medusa-demo-v9-reset-state-gateway-scores.json
python -X utf8 -B sentinel/local-platforms/import_gateway_scores.py --log sentinel/local-platforms/.runtime/fixture-gateway.log --evidence sentinel/local-platforms/reports/medusa-demo-v9-payment-alternative.json --output sentinel/local-platforms/reports/medusa-demo-v9-payment-alternative-gateway-scores.json
python -X utf8 -B sentinel/local-platforms/audit_medusa_runtime.py --sync-inventory
python -X utf8 -B sentinel/local-platforms/reconcile_medusa_user_document.py
```

完成後於18444入口終端機Ctrl+C停止獨立入口；不停止既有Medusa及其他服務。原始77API文件快照不改，這份文件獨立說明目前版本可用參數與行為。

本輪12項runtime／文件／業務證據測試通過，Python語法與公開紀錄憑證遮蔽檢查通過。額外18444入口於補測完成後已停止；既有9100、18085、18443保留。模型檔SHA未改。

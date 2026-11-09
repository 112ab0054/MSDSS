# Medusa 驗證與展示

2026-11-10，依使用者確認「還原原始77項，保留密碼重設請求」執行，取代先前刪除reset-password的指示。沒有刪其他功能、修改模型／訓練資料、修改既有Medusa服務、Mirage或根compose。

## 原77項與79項的差異

以原始文件快照parse出的77組方法＋路徑為準，逐一集合相等核對，不是任意刪兩項湊數。根目錄Medusa_77_API_填寫參數.md已從凍結快照逐bytes還原，API標題、參數、說明與範例不改。

從當前參考清單移出的只有先前額外加入的：

- POST /store/search
- POST /store/payment-collections/{id}/payment-sessions/{session_id}

POST /auth/customer/{auth_provider}/reset-password仍在原77項中。兩個額外操作及79項還原前完整清單保存在[歷史目錄](history/2026-11-10/)，原HTTP、分數與失敗證據不刪除。

目前[參考清單](api-extension/medusa-holdout-inventory.json)77項：60成功、1部分成功、7前置不足、9功能／版本差異，not_run=0。歷史補測共357筆HTTP中，352筆對應當前77，5筆是移出的額外操作；這些原有請求不是本輪重跑。原32項復核表中的兩項以excluded標註，保留先前原因。

## 77項參考清單與gateway偵測範圍分開

77項僅供文件、展示功能與平台驗證，不再是模型篩選條件。app.py移除清單讀取、固定79數量檢查與selected_operation路由比對，Docker建置不再要求複製清單。

所有經gateway、支援的GET／POST／PUT／PATCH／DELETE／OPTIONS／HEAD都分析，包括管理API、未知路徑、清單外的方法及編碼路徑。原77清單裡的每一項也繼續分析。不支援WebSocket；直接連Medusa或未經此gateway的網站流量不會被自動攔截。

模型維持觀察模式，SQLi／XSS也照樣轉送；後端仍按自己的認證與路由規則回200、401、404等，gateway不把後端拒絕改成成功。所有路徑均進模型不代表模型對所有路徑的準確率已獲驗證。

## 模型忙碌不再略過

以asyncio.Lock序列使用模型，後續請求排隊等待。GATEWAY_ANALYSIS_TIMEOUT保留原環境變數名稱，語意改為等待告警門檻（預設0.2秒）：超過會記analysis_slow，仍等待該筆推論完成，沒有analysis_busy略過。模型忙碌、慢速或高併發會增加回應延遲；這個值不是硬性逾時上限。

客戶端取消時，已開始的推論由shield保護；下一筆會先等未完成的前一筆。模型未載入或推論出錯仍轉送並記錄，不能宣稱這些例外也已成功預測。Docker啟動入口仍要求模型載入與自測成功。

## 驗證與本機執行狀態

- 19項gateway測試通過：原77＋未知路徑都分析、管理API與HEAD／OPTIONS分析、忙碌兩筆均完成、真XGBoost載入與分數日誌、轉送bytes／Cookie／壓縮回應及遮蔽。
- 12項runtime／文件測試通過，包含參考清單與原77文件集合完全相等、reset-password確實保留。
- 已只重啟本專題自行建立的18085 HTTP及18443 HTTPS入口，使本機正在運作的gateway也使用新程式；仍只綁127.0.0.1並連既有9100。原Docker Medusa、Mirage、storefront未重啟／改設定，沒有遠端部署或宣稱既有Docker映像已更新。
- 真實網路補驗6筆gateway請求及6筆直連對照：GET商品200、GET /admin/users 401、未知路徑404、OPTIONS商品200、HEAD商品200、POST商品404；gateway與直連狀態全部一致，商品ID也一致。
- 6筆gateway請求都以UUID對上真實模型日誌，包含原本清單外路徑。這是接線驗證，不是分類準確率。

[實際HTTP及斷言](../local-platforms/reports/medusa-gateway-all-paths-2026-11-10.json)、[實際模型分數](../local-platforms/reports/medusa-gateway-all-paths-scores-2026-11-10.json)。與舊79平台驗證的357筆分開保存，不混算平台成功數。

模型SHA仍e612214de592b01ec931cc73a100603928c89e747c61eebf3027424669f24993；模型、特徵及推論數學未修改，不需因本次接線調整重新訓練。

## 交付給隊友

執行必需：gateway的app.py、docker_start.py、requirements.txt、Dockerfile及Dockerfile.dockerignore、完整gateway/model/；共享model/predict.py、features.py、request_input.py及requirements.txt。保留.gitattributes對gateway/model的原始bytes規則。API清單與原77MD作為文件交付，已不是gateway啟動相依；歷史備份與本機補測工具可由主專題repo保存。

部署主機需重啟Python程序或重新建置gateway映像才會套用；不要覆蓋隊友compose／.env。更新後應看model_ready並實際送一筆清單外API，確認有同UUID的prediction日誌。啟動與等待語意見[gateway README](../gateway/README.md)。

## 已完成的正常流程與已知限制

目前真實Medusa2.21.0的正常主流程已涵蓋商品、註冊登入、購物車新增／修改／移除、會員地址、固定費率配送、pp_system_default離線測試付款、建立與查詢訂單。不是實際扣款或全部77個操作成功，也不是商城瀏覽器端到端驗收。

後續已補通真實促銷套用／移除、集合／標籤／商品類型／退貨原因明細、密碼更新、通用驗證碼確認與退貨要求。促銷總額20降為18，移除恢復20；退貨前只履約本輪新測試訂單，建立退貨後狀態requested，查回申請數量1，不宣稱已收貨或退款。

原生取碼工具只處理自己的帳號／訂單，不杜撰Token。密碼更新確認舊密碼401、新密碼登入同一顧客；通用驗證碼確認後verified_at非空，同碼重用被拒絕。訂單移轉接受／拒絕使用平台原生產生Token，並查雙方訂單歸屬與confirmed／declined狀態。取碼途徑是本機原生workflow／唯讀查詢，並非郵件送達。

Cookie成功範圍是驗證憑證的真正HTTPS與CookieJar自動維持Secure Cookie；移除Bearer仍可讀本人，登出後再查401。HTTP18085不能據此說Secure Cookie也已成功。私有TLS憑證效期有限，過期須換新，不安裝系統信任、不關閉客戶端驗證。

| 未完成項目 | 原因及目前證據 |
| --- | --- |
| reset-password部分成功1項 | HTTP確實建立新Token資料列、舊Token失效；不存在帳號也回201但不產生Token。未觀測該HTTP事件消費或郵件送達。event-bus-local僅有訂閱者時記Processing，沒log不代表沒事件。 |
| MFA前置不足5項 | 目前9100服務缺MFA encryption key，沒有可用真實因子／挑戰／備援碼，未改現有認證設定。 |
| OAuth callback前置不足1項 | 僅emailpass，未配置第三方提供者與應用憑證。 |
| 動態配送計價前置不足1項 | manual_manual的canCalculate=false，calculatePrice明確拋錯；原HTTP500保留。固定費率配送已通，不代表動態計價可用。 |
| 功能／版本差異9項 | locales的translation模組停用；另外8項是目前2.21.0未提供的信箱驗證專用路由、禮卡與商店額度路由。沒有拿未發行資源ID冒充成功。 |

## 目前版本可用的替代方式

- 搜尋使用GET /store/products?q=商品名稱，已以真實商品名稱查回同一ID，不存在名稱回空清單。GET /store/products/search雖有路由，實測No search index registered for product，沒有商品搜尋索引，不能只換路徑就說通過。POST /store/search不在原77中，也不適用目前9100實例。
- 付款session使用POST /store/payment-collections/{id}/payment-sessions，Body為provider_id及data。同集合再次建立可保存新marker，但session ID會改變，須使用回應的新ID，不能宣稱更新原ID。只用pp_system_default、狀態not_paid，沒有授權或capture。原額外的session/{session_id}更新不在原77中。

## 參數與歷史版本差異

原始77文件及bundled OpenAPI不能直接當成功執行證據。先前獨立2.22.4實例與目前9100的2.21.0分開紀錄，前者結果不加進後者成功數。

先前2.22.4的兩次真實建車／下單與原生Zod探查確認：shipping_address／billing_address只送實際地址欄位，地址id／created_at／updated_at由後端產生，不能按回應模型當必要輸入；items使用variant_id與quantity，不送伺服器產生的line-item id。只有quantity時缺variant_id，沒有自己杜撰商品ID。

舊獨立2.22.4另測到session更新需client_data，而非data，但離線提供者未證明PSP特定更新效果；另有POST /store/search可用。這兩項是版本不同且不在原77的額外行為，不改寫目前API清單或原文件參數。先前獨立2.22.4曾完成MFA因子與備援碼生命週期，challenge驗證仍缺正常登入產生的challenge；不能拿那個實例的設定替目前9100缺金鑰的5項轉成功。

歷史原始證據保留於local-platforms/reports：medusa-72caa767eed84dcead80c23929ac09b5.json、medusa-0b64cbb3dffd446d9dc36f2bd9c9ec58.json、medusa-cart-validator-probe.json、medusa-mfa-cf90592d78914c559ef5c9e935125a1b.json。驗證器探查是schema測試，不是HTTP業務驗收。

## 目前證據索引與補測入口

| 證據 | 檔案（相對sentinel/local-platforms/reports） |
| --- | --- |
| 77項實測狀態與每項理由／UUID | medusa-demo-v9-runtime-status.json、medusa-demo-v9-api-status.csv |
| 原32項與原77文件逐欄對照 | medusa-demo-v9-user-document-audit.json／csv |
| 主要購物流程 | medusa-demo-v9-flow.json |
| 原生資料補齊、促銷、密碼更新、履約及退貨 | medusa-demo-v9-fixture-checks.json、medusa-demo-v9-native-fixture-provenance.json |
| 真實HTTPS Cookie | medusa-demo-v9-document-input-checks.json |
| 訂單移轉 | medusa-demo-v9-native-token-transfers.json、medusa-demo-v9-native-token-provenance.json |
| 通用驗證碼 | medusa-demo-v9-verification-fixture-checks.json |
| HTTP重設Token生成／失效 | medusa-demo-v9-reset-state-checks.json、medusa-demo-v9-reset-state-proof.json |
| 搜尋與付款替代路徑 | medusa-demo-v9-search-alternatives.json、medusa-demo-v9-payment-alternative.json |
| 環境、外掛與事件日誌條件 | medusa-demo-v9-document-environment-proof.json、medusa-demo-v9-followup-source-proof.json |

主要重跑工具在local-platforms：run_medusa_demo_flow.py、run_medusa_fixture_checks.py、run_medusa_verification_fixture.py、run_medusa_reset_state_checks.py、run_medusa_payment_alternative.py。補測18444入口用start_medusa_fixture_gateway.py，需有效私有TLS憑證及.runtime/medusa-demo.json，不重複啟動已佔用的埠；完成後只停這個入口。工具只操作自己新建測試資料，會更新latest報告，不平行執行同套工具。

audit_medusa_runtime.py --sync-inventory及reconcile_medusa_user_document.py可整理現行JSON／CSV狀態；分數從實際gateway日誌按UUID取得，不以離線重算補造。HTTP負向對照、schema探查與正常成功要分開，HTTP200不代表完整業務驗收，模型分類也不由HTTP狀態決定。

2026-11-10文件清理：已將多份分階段Medusa說明合併至本頁。原始HTTP、分數、設定證據、API原文快照與授權未刪；更早歷程由Git與白話紀錄追溯。

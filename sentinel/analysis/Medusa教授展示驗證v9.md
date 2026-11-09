# Colab v9模型與Medusa教授展示驗證


**最新依原文件復核：51成功、3部分成功、14前置不足、11版本／功能差異，not_run=0。Cookie兩項在真正HTTPS補測成功；移轉接受／拒絕也通過，通知送達未測；配送500已定位manual不支援動態計價，改列前置不足。** 詳見[原文件逐項復核](Medusa依原API文件逐項復核.md)。以下先前統計／未定位原因為歷史，原始HTTP失敗紀錄仍保留。


**最新補測已完成：79項都有HTTP紀錄，runtime_status的not_run=0；47成功、2部分成功、18前置不足、11版本／功能差異、1實測失敗。HTTP覆蓋含負向探查，並非79個正常流程都成功。** 172筆HTTP與實際gateway分數逐筆對應，完整清單與阻礙見[補測及runtime同步](Medusa剩餘API補測與runtime同步.md)。以下58筆流程與42項成功表為第一輪快照。

已使用使用者提供的 results_download (6).zip 取代專案內舊模型，沒有重新訓練、修改權重或調整分類門檻。四份資料SHA與small-api-v9一致；2402維特徵v6、輸入v3、normal／sqli／xss順序相容；完整manifest與三筆跨環境自測通過。

## 實際接線

本機API入口：**http://127.0.0.1:18085** → 新Sentinel gateway → **http://127.0.0.1:9100** 真實Medusa **2.21.0**。原保存規格標示2.22.3、原獨立測試平台2.22.4，不假裝版本一致。

這次沒有改根compose、Medusa服務設定或資料庫結構，沒有修改Mirage或原網站流量路由。原網站的Mirage gateway仍是另一套；本紀錄驗證的是18085 API入口，不是已將原網站全站切成新模型。測試僅經正常API建立測試顧客、購物車與一筆測試訂單，不會改商品／後台設定。

## 正常購物實測

58筆真實HTTP請求，58筆均有實際gateway推論日誌，使用X-Request-ID UUID逐筆比對；不以事後重算冒充線上分數。36項業務斷言全部通過。流程結果passed_with_limitations，下面有具體限制，不稱79個API全通過。

動態取得商品、變體與region → 註冊／Bearer登入／刷新token／讀回本人 → 新增並更新地址 → 建立購物車並綁定顧客 → 合併數量2、改成3、移除後確認空車、重新加1 → 選manual_manual配送 → 選pp_system_default原生離線付款 → 建立訂單並重新讀回。

訂單已核對pending、正確顧客email、variant與數量1、地址、配送選項、payment authorized、captured_amount=0。這是本機離線付款授權，**沒有真實扣款**。測試結束移除了本次顧客地址；測試顧客、未結帳購物車及測試訂單仍留作證據，不自動刪資料。

## 正常操作仍有誤判

本輪58筆正常意圖中55筆判normal、2筆判XSS、1筆判SQLi。這是小型流程探針的觀測數，且包含前置條件／路由失敗請求，不代表整站正式誤報率。

| 正常操作 | 模型判定 | normal | SQLi | XSS |
| --- | --- | ---: | ---: | ---: |
| GET /store/product-categories/{id} | xss | 41.03% | 6.59% | 52.38% |
| POST /store/carts/{id}/shipping-methods | xss | 38.85% | 5.16% | 55.99% |
| POST /store/payment-collections/{id}/payment-sessions | sqli | 23.34% | 52.53% | 24.14% |

目前**只告警、不封鎖**，所以誤判不會阻斷上述購物流程。分數未校準，不是攻擊發生機率或模型準確率；沒有為了明天展示把這三筆改成normal。

## 額外唯讀搜尋探針

只以GET /store/products的q字串測試模型，不執行腳本或破壞資料。三筆正常搜尋、兩筆SQLi形態與兩筆XSS形態均由真實Medusa回200商品清單；200不代表攻擊成功或存在漏洞。所有案例完整保留，沒有只挑成功辨識者。

| q內容 | 測試意圖 | 模型輸出 | 該輸出分數 |
| --- | --- | --- | ---: |
| `cotton` | normal | normal | 71.63% |
| `shirt` | normal | normal | 71.42% |
| `blue bag` | normal | normal | 52.70% |
| `' OR 1=1 --` | sqli | sqli | 73.27% |
| `1 AND 1=1` | sqli | normal | 70.41% |
| `<script>alert(1)</script>` | xss | xss | 94.84% |
| `<img src=x onerror=alert(1)>` | xss | xss | 89.49% |

其中`1 AND 1=1`判normal，證實SQLi涵蓋仍有弱點；不能宣稱所有SQLi／XSS都會被攔下。

## 79個選定API第一輪狀態（歷史快照）

| 狀態 | 數量 |
| --- | ---: |
| 尚未測試 | 29 |
| 成功 | 42 |
| 前置條件不足 | 6 |
| 版本／功能差異 | 2 |

逐項表：`../local-platforms/reports/medusa-demo-v9-api-status.csv`。成功表示該操作至少一次有對應斷言，不代表所有參數與分支全覆蓋。前置不足包括空目錄無明細ID、Cookie session；未測試項目含其他認證／MFA／轉移等額外情境，不猜測它們必然失敗。

### 已知差異與限制

- GET /store/locales：展示站404，路由／功能未提供，不列成功。
- POST /store/payment-collections/{id}/payment-sessions/{session_id}：展示站404；建立離線付款session及建單成功，更新路由不列成功。
- POST /auth/session回200，但本次HTTP入口沒有可用Cookie維持登入；移除Bearer後GET本人401，DELETE session也401。Cookie原因尚未定位，不宣稱已證明是secure/domain或版本造成。展示流程使用真實Bearer，不能聲稱Cookie登入已完成。
- 目錄collections、product-tags、product-types、return-reasons為空，無對應明細ID；不捏造ID湊測試。
- 這是離線訓練模型在Medusa的實際推論探針；訓練metadata仍保留offline／exploratory／platform_http_verified=false，不將Medusa測試回填訓練資格或用來重訓。

## 重跑方法

在專案根目錄，先安裝gateway/requirements.txt，再於獨立PowerShell視窗啟動：

```powershell
$env:MEDUSA_UPSTREAM='http://127.0.0.1:9100'
python -m uvicorn app:app --app-dir sentinel/gateway --host 127.0.0.1 --port 18085 --no-access-log
```

預設會載入專案新模型，日誌應顯示model_ready。若機器有設舊GATEWAY_MODEL_DIR，須先移除或改指目前sentinel/gateway/model。結束此獨立入口用Ctrl+C，不需停止原Medusa或Mirage。

另一視窗執行：

```powershell
python -X utf8 -B sentinel/local-platforms/run_medusa_demo.py --base-url http://127.0.0.1:18085 --output sentinel/local-platforms/reports/medusa-demo-v9-rerun.json
```

使用私有`.runtime/medusa-demo.json`的publishable_api_key，該檔不進GitHub；本機已準備。其他電腦必須提供自身商店的金鑰，不能直接套公開紀錄中的REDACTED。每次重跑使用新測試帳號，從回應取商品／地址／車／配送／付款／訂單ID；不要把舊報告的固定ID當成重現流程。

終端會列每步HTTP狀態；gateway另一視窗列request_id、判定及三類分數。API本身回應仍來自Medusa，沒有為展示改成假回應。完整遮蔽證據在medusa-demo-v9-flow.json，模型分數在medusa-demo-v9-predictions.csv，狀態及摘要同資料夾。

## 模型與歷史結果

當前模型SHA：`e612214de592b01ec931cc73a100603928c89e747c61eebf3027424669f24993`。Colab結果原樣保存於sentinel/model/results/colab-v9-2026-11-09，完整推論ZIP為sentinel/model/inference-v9.zip；舊gateway v7套件在history/model-v7-before-colab-v9。未攜帶Colab的__pycache__。

Colab資料：test accuracy82%、Sylius82.67%、challenge72.92%；challenge SQLi recall18.75%。這些是原離線評估，不能拿本輪少量Medusa探針當成正式泛化準確率。


驗證完成：60項模型工具測試與16項gateway測試通過；模型套件原始manifest、自測與準備提交的Git內容SHA核對通過。所有提交檔案及ZIP已掃描確認未含本次真實商店金鑰，.runtime與__pycache__未納入。

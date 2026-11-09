# 已接入的 XGBoost 模型與推論說明


最新Medusa狀態：79項均有HTTP紀錄且清單runtime_status已同步，not_run=0；47成功、2部分成功、18前置不足、11版本／功能差異、1實測失敗。含負向探查，不代表79個正常流程全成功。[最新逐項補測](../analysis/Medusa剩餘API補測與runtime同步.md)。下文42成功／29未測屬第一輪歷史。

目前模型為使用者上傳的Colab v9（results_download (6).zip），四份資料SHA與small-api-v9一致，特徵v6／2402維，沒有另行調參或改權重。舊v7完整套件已保存在../model/history/model-v7-before-colab-v9。下方v5／v6／v7探針為歷史，當前真實Medusa結果見[教授展示驗證](../analysis/Medusa教授展示驗證v9.md)。
已核對原 `bundle-manifest.json`，只保留其中列出的檔案與清單本身，不攜帶 Python 3.13 的 `__pycache__`、全部訓練／測試請求或其他評估產物。
來源摘要在 [model-source.json](model-source.json)，原套件在 [model/](model/)。

## 檔案與用途

| 位置 | 用途 |
|---|---|
| `app.py` | 載入模型、判斷 79 個 API、建立模型副本、記錄預測，再轉送原請求 |
| `../model/predict.py` | 專案推論入口，核對套件、轉換特徵並呼叫 XGBoost |
| `model/model.json` | 使用者已訓練完成的樹模型權重 |
| `model/metadata.json` | 特徵／輸入版本、類別順序、header 順序、布局及離線標記 |
| `model/predict.py` | 原訓練輸出的同版推論程式副本，附詳細中文註解 |
| `model/features.py` | 本次重訓輸出的 v6 特徵，產生 2402 維數值向量 |
| `model/request_input.py` | 原訓練輸出的請求整理與憑證遮蔽規則 |
| `model/self-test.json` | 三類各一筆 train 探針及原環境機率，用來檢查計算一致性 |
| `model/bundle-manifest.json` | 原套件逐檔 SHA-256，包含程式註解與空白 |

專案入口與套件內的 `predict.py`、`features.py`、`request_input.py` 內容一致，Predictor 會核對 Python 實際 import 到的檔案。
不要單獨改寫 `model/` 內的程式、metadata 或 manifest；修改推論實作時需以可信來源更新整套相容產物，不能只刪檢查。

## 一筆請求的執行順序

1. 啟動時，`lifespan` 以 `Path(__file__)` 找 `model/`，或使用環境變數 `GATEWAY_MODEL_DIR` 指定的新套件。
2. `Predictor(directory)` 讀取 manifest，核對必要檔案、SHA、版本、三類順序與特徵維度，再將 JSON 權重載入 `XGBClassifier`。
3. `self_test()` 重算三筆訓練探針的機率；誤差須在指定浮點容許範圍內。通過才把物件存進 `app.state.predictor`。
4. 收到 HTTP 請求，`selected_operation(method, raw_path)` 比對既有 79 操作清單；其他路徑／方法直接轉送，不呼叫模型。
5. 選定操作進入背景分析，`model_request` 建立包含 method、path、query、headers、body 與原文的副本。只在模型副本遮蔽密碼、Cookie、token 等憑證。
6. `predictor.predict` 呼叫同版 `features`，產生 2402 維：基本方法／格式、文字與 header 統計，以及 query、body、path、headers 四通道的字元片段雜湊。
7. `predict_proba([vector])[0]` 得到 normal／sqli／xss 三類分數，再以 `argmax` 取最大值。沒有另加 0.5 或 0.9 門檻，機率也未經校準。
8. 日誌只記類別、三類機率、`mode`、`exploratory`；`client.send` 將原始請求交給後端，沒有把遮蔽值送給 Medusa。

目前模型為 **offline、exploratory=true、platform_http_verified=false**。這些標記保留原樣，套件自測不能證明平台漏洞、攻擊成功或真實防護率。
模型忙碌／超時時，沿用觀察模式繼續轉送；可能有請求未完成模型分析，不能聲稱每筆都已偵測。

## 啟動及確認

在專案根目錄：

```sh
python -m pip install -r sentinel/gateway/requirements.txt
python sentinel/gateway/model/predict.py --model sentinel/gateway/model --self-test
python -m uvicorn app:app --app-dir sentinel/gateway --host 127.0.0.1 --port 8080 --no-access-log
```

上游預設是 `http://127.0.0.1:9000`；可用 `MEDUSA_UPSTREAM` 改成實際 Medusa 的 HTTP(S) origin。
模型載入成功會顯示 `model_ready mode=offline exploratory=True`。若有 `model_load_failed`，表示目前只有轉送，請先檢查完整套件與依賴。
選定 API 的預測日誌會附 `probabilities`，讓你確認不是只收到請求而沒有推論。非選定 API 不產生預測紀錄。
日誌是推論輸出，沒有拿它當作已標註的準確率或召回率。

歷史v5模型曾在Linux／Python環境完成套件探針與真實推論接線測試，目前v6已在Windows驗證，包含中文／空白路徑搬移。
另有本機 HTTP 傳輸測試；不代表已替實際 Medusa 網站完成登入、CORS 或 79 個業務流程驗收。

## 歷史v5實際HTTP接線探針（非目前模型）

已另外啟動真實 uvicorn gateway，連到本機 TCP 測試上游，使用原模型取得以下結果：

| 請求意圖 | 原模型輸出 | 上游是否收到 |
|---|---|---|
| 一般商品查詢 `cotton` | SQLi | 是 |
| 查詢內含 SQLi 字串 | SQLi | 是 |
| 購物車本文內含 XSS 字串 | SQLi | 是 |
| 清單外的請求 | 不呼叫模型 | 是 |

結果保存於 [model-connection-verification.json](model-connection-verification.json)，包含三類分數、原模型 SHA 與測試範圍。
這代表接線可用，也顯示正常查詢誤報與攻擊類別混淆；沒有為改善表面結果重新訓練或調整門檻。
這幾筆只是接線探針，不是新的準確率測試；本機上游不是 Medusa，亦未證明任何漏洞成功。

## 歷史v6修正結果

正常查詢的20個固定模型探針皆判normal，包括HTTPX Accept:*/*及application/*；不代表真實網站誤報率0%。完整改版、分數與取捨見[白話紀錄](../analysis/訓練版本與問題處理白話紀錄.md)，證據見normal-probe-v6-2026-11-09。當前權重是在Windows固定依賴重訓及驗證，先前Linux驗證只屬歷史v5套件；v6仍須目標環境自測。

## 資料v7正常值修正後模型

歷史v7曾以small-api-v7固定參數重訓，特徵仍v6，未修改分類門檻；舊v6權重另存history/document-values-before。當前模型來源與SHA以model-source.json為準。資料修正及最新數據詳見白話紀錄，不把歷史v5／v6探針當成當前結果。實際Medusa業務驗收仍未完成。


## 目前Colab v9及真實Medusa驗證

新模型完整manifest及三類探針自測通過，16項gateway測試通過。真實Medusa2.21.0的58筆正常流程請求與7筆唯讀搜尋探針，全部有UUID對應的實際gateway分數。正常流程36項斷言通過並建立未扣款的離線測試訂單，但58筆正常意圖有3筆誤判；Cookie及2個缺少路由另列限制，不能說79個API全成功。

目前79操作狀態：42成功、6前置不足、2版本／功能差異、29未測。獨立展示API入口18085連現有真實Medusa9100，原Mirage／storefront未改線。已測資料與分數見教授展示驗證；不要把舊v6正常20探針當成v9整站零誤報。

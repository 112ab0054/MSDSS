# XGBoost：Colab 訓練與可搬移推論

## 目前 Colab 使用方式：離線實驗

開啟 [msdss訓練.ipynb](msdss訓練.ipynb)，上傳 [dataset.zip](dataset.zip)，由第一格重新執行。Notebook 預設 `MODE="offline"`，目前 420 筆生成資料可訓練，不再要求不存在的 HTTP／session 證據。平台、標籤、原始輸入格式、配對及跨集合隔離仍檢查。

```sh
python train.py --mode offline --data-dir PATH_TO_SPLITS --output NEW_RUN_DIRECTORY
```

離線模式產生完整的 test／validation 評估與可搬移 inference.zip，metadata、報告及推論結果均標示 `mode=offline`、`exploratory=true`、`platform_http_verified=false`。保留原資料的未送出狀態，不改旗標，不把相依群組當真實 session。這是生成請求的分類實驗，不能宣稱已在平台重播、攻擊成功或具備部署效果。

`--mode live` 保留 HTTP、v3 原文、session 與來源證據對帳；CLI 預設 live，Notebook 明確指定 offline。`--allow-candidates` 是舊有流程測試選項，與新的 offline 模式不同。以下實機要求只適用 live；無需為離線訓練另造實機證據。

2026-11-09 CSV 顯示更新：現行 small-api-v2 的 train/test/validation 已移除「實際送出」「可正式訓練」兩欄；完整紀錄 JSON、請求、標籤、集合與內部 HTTP 證據檢查不變。舊歷史檔保留原狀。

2026-11-09 更新：依使用者要求移除人工審核及其訓練資格判斷。新版 Colab 套件為 [dataset.zip](dataset.zip)，舊 ZIP 不覆寫。仍保留真實 HTTP、原文、來源證據、標籤與集合隔離檢查。

程式使用明確的 train/test/validation 三份 CSV，不重新分割。目前 small-api-v2 是未實機採集的生成資料；使用 offline 模式可以訓練，live 模式仍會停止。 沒有正式模型或真實效果分數。

## 資料與評估規則

- train/test：Bagisto＋Shopware；validation：僅 Sylius＋外部 payload。Medusa 不參與。
- 預定小版本 252/84/84，各集合三類等量；程式不強迫固定筆數，會核對平台、三類、來源和集合隔離。
- session、正常／攻擊配對、來源證據、家族及重複群不可跨集合。發現衝突直接停止，不重新洗牌。
- 事前固定 CPU、150 棵樹、深度 3、learning_rate=0.05、seed=42。沒有以 test 或獨立 validation 做 early stopping 或選參數；如果以後要調參，只能在 train 內另做分組驗證。
- live 模式不要求人工審核、training_approved、reviewer、reason 或 candidate_sha256。live 輸入仍須包含標籤、v3 原文、真實 session、明確 HTTP 已執行旗標；核對實際證據 SHA、request ID、狀態和請求內容。舊 audit 紀錄可保留，但不決定訓練資格。
- `--allow-candidates` 只供原文／來源證據不完整的流程測試；**仍拒絕 http_executed=false 的計畫**。試跑套件帶 exploratory 標記，正式閘道拒絕載入。

## 在 Colab 操作

1. 開啟 [msdss訓練.ipynb](msdss訓練.ipynb)，上傳至 Colab。
2. 第一個程式格上傳 [dataset.zip](dataset.zip)。目前隨附生成資料，可在 offline 模式取得離線分類成績。
3. 目前使用 offline 模式；若之後切換 live，才需要完成真實採集與證據對帳，重新打包 CSV 和遮蔽證據。
4. Notebook 分開顯示 test 與 validation 報告，可畫混淆矩陣、ROC、PR 圖，最後下載結果 ZIP。

重新打包（在專案根目錄；output 必須是新檔名）：

```sh
python sentinel/model/prepare_colab.py --data-dir sentinel/dataset/small-api-v2 --output colab_upload_new.zip
```

正式訓練資料須加入證據根目錄：

```sh
python sentinel/model/prepare_colab.py --data-dir PATH_TO_COLLECTED_SPLITS --evidence-root PATH_TO_EVIDENCE_ROOT --output colab_collected.zip
```

每份 CSV 至少有 `完整紀錄JSON` 欄位，其值包含 input、metadata、sample_id，以及 annotation.label／annotation.proposed_label 或頂層 label。audit 是選填的歷史紀錄，不要求審核工具匯出。證據根目錄下保留 source_evidence 的相對子目錄，例如 sentinel/dataset/evidence。只打包被引用的已遮蔽 reports/evidence，絕不打包 .runtime、密碼設定、三個平台或整份專案。

訓練套件包含 header-schema.json，直接保存三份人工 API 文件的 12 種 header 名稱和來源 SHA，Colab 不需連回原電腦或讀取 API 文件。更新 API 文件後應重新打包。

## 本機執行相同程式

Python 3.11–3.13，建議 3.12。Windows 和 Ubuntu 均使用獨立環境安裝 requirements.txt。以下指令在程式所在資料夾執行：

```sh
python -m pip install -r requirements.txt
python train.py --mode live --data-dir PATH_TO_COLLECTED_SPLITS --evidence-root PATH_TO_EVIDENCE_ROOT --output NEW_RUN_DIRECTORY
```

可用 `--trees 150` 明確宣告樹數，必須在看保留資料成績前決定。CLI 路徑來自參數；模型預設位置由 predict.py 本身定位，沒有 C 槽、/content 或原 repository 的固定依賴。輸出拒絕覆蓋非空實驗目錄。

## 輸出數據

根目錄有 summary.md、experiment.json、split.csv、inference.zip。test/ 與 validation/ 各有：

- report.md／report.json：整體、逐類與逐平台成績。
- metrics.csv：Accuracy、Balanced accuracy、Macro Precision／Recall／F1、Weighted／Micro-F1、MCC、Kappa、Log loss、Brier、正常誤報率、攻擊偵測召回率及漏報率。
- per-class.csv：各類 Precision、Recall、F1、樣本數、Specificity、FPR、FNR。
- confusion_matrix.csv：實際筆數；confusion_matrix_normalized.csv：逐列比例，列為真實、欄為預測。
- curves.csv：逐類 one-vs-rest ROC／PR 曲線座標和門檻；逐類 ROC-AUC、Average Precision 在 report.json。
- predictions.csv：樣本 ID、群組、真實／預測類別和三類機率，不輸出完整請求。
- 永遠猜訓練多數類的比較基準、特徵相同的跨集合數、群組隔離、資料／程式 SHA、版本、訓練時間、median/p95 單筆推論延遲。
- 95% 群組 bootstrap 區間；少於 20 個獨立群組不報，不能把 140 組配對當成 140 次獨立購物流程。

Colab 圖表格在有 Matplotlib 時另存 PNG；沒有繪圖套件仍能輸出全部 CSV/JSON。機率未校準；AP 不等於梯形積分 PR-AUC。高分只描述指定資料，不能宣稱平台存在漏洞或模型保證防禦成功。

## 搬到 Windows／Ubuntu 推論

解壓 inference.zip，整個資料夾一起搬。裡面有 model.json、metadata.json、predict.py、features.py、request_input.py、requirements-inference.txt、bundle-manifest.json、自我檢查樣本及說明。不使用 pickle/joblib，也不依賴 API 文件或訓練資料。

在解壓目錄執行：

```sh
python -m pip install -r requirements-inference.txt
python predict.py --self-test
python predict.py request.json
```

從其他資料夾也可指定 predict.py 的完整路徑；未指定 --model 時會尋找程式旁的模型。若呼叫主專案的 predict.py，需用 --model 指向整個推論套件，且當前程式必須與套件內版本一致。

載入時核對套件 SHA、程式實際載入內容、輸入／特徵／類別版本、Header 順序及模型維度。自我檢查以三類代表請求比對訓練環境機率（容許浮點誤差 1e-6）。requirements-inference.txt 依真正訓練版本產生，Windows／Ubuntu 使用 CPU，不需要原 Colab GPU。

**跨系統相容性必須在各系統執行 self-test 才算驗證。** 本機測試結果另見 PORTABILITY_CHECK.md，不把目錄名稱模擬或上游格式保證當成 Ubuntu／Colab 的實測。

## 原始輸入與歷史紀錄

request_input_version=3 保留一般 ID、Email、大小寫、空白和編碼，只遮蔽密碼、Token、Cookie、Key 等憑證；不做字串正規化。特徵 VERSION=4，278 維統計基準，全部輸入位置參與；這不是原文字元語意模型。SENSITIVE 欄位不使用值或真實長度。

舊 195 筆正常證據、small-api-v1/v2 不覆寫、不自動核准；歷史未記錄的 raw bytes 不補造。先前 260 筆與 Sylius 分數來源不明，不作研究證據。舊命令的 --test-platform 與單檔自動分割流程已移除。


## small-api-v2 訓練前檢查（本次更新）

先檢查，不訓練；若資格不符回傳退出碼 2，列出所有集合的問題：

```sh
python sentinel/model/train.py --check-only --evidence-root .
```

未指定 --data-dir 時，預設由程式位置找 sentinel/dataset/small-api-v2，不依賴 Windows 磁碟機字母。原始碼專案中使用上方指令；Colab 解壓縮套件後，Notebook 會明確指定 data、evidence 的所在位置。

完成實機採集與證據對帳後，再執行：

```sh
python sentinel/model/train.py --data-dir sentinel/dataset/small-api-v2 --evidence-root . --output runs/experiment-001
```

目前儲存庫內的 420 筆仍是未送出計畫，上述 live 命令應停止，offline 命令可訓練；--allow-candidates 也不允許未送出計畫。Bagisto 來源快照已經由完整重建與資料逐檔比對對帳；原紀錄保留在 small-api-v2/history，詳見 source-reconciliation.json。候選仍須實機採集與證據對帳。

Colab Notebook 已加入前置檢查；prepare_colab.py 同時打包 preflight.py 與原始 provenance.json。test 與獨立 validation 的成績仍各自輸出，不用於選參數。套件內的 self-test.json 改從 train 取樣，不帶入保留測試資料。

模型輸出仍含 Accuracy、各類 Precision/Recall/F1、Macro/Weighted/Micro-F1、混淆矩陣、誤報／漏報、ROC/PR 曲線資料、MCC、Kappa、Log loss、Brier score 與基準比較。可搬移性測試在 Linux 的中文／空白路徑執行；尚未宣稱在 Colab、Windows 或 Ubuntu 各自完成實機訓練／推論驗收。

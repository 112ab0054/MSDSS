# Sentinel

最新補資料實測：60成功、1部分成功、7前置不足、11版本／功能差異，not_run=0；339筆HTTP與實際gateway分數匹配，184項業務斷言通過。促銷、四種目錄明細、密碼更新、退貨及通用驗證碼已補通；通知／郵件送達仍未驗證。 [本輪實測紀錄](analysis/Medusa補測資料建立與驗收.md)


最新Medusa狀態（依原文件復核後）：79項均有HTTP紀錄，not_run=0；60成功、1部分成功、7前置不足、11版本／功能差異。Cookie成功限真正HTTPS；移轉接受／拒絕使用原生token、通知送達未測。配送500保留，但已證實manual不支援動態計價，改列前置不足。[最新逐項補測](analysis/Medusa剩餘API補測與runtime同步.md)。下文42成功／29未測屬第一輪歷史。


最新模型：已接收使用者Colab v9輸出，更新gateway完整推論套件與inference-v9.zip；原v7套件保留。真實Medusa正常購物與離線建單完成，58筆正常意圖有3筆誤判，79操作中42項成功，其他狀態另列。[教授展示驗證與啟動方式](analysis/Medusa教授展示驗證v9.md)。下文「gateway仍v7／尚未重訓」為之前資料修正階段的歷史紀錄。

Sentinel 是本專案規劃中的 XGBoost 電商 API 請求分類模組。目前已有契約、API 參數文件與研究計畫，尚無正式訓練資料、模型或線上推論服務。

目前離線資料為small-api-v9：train702／test150／Sylius validation150／challenge96，共1098筆；依文件修正正常控制填值，特徵仍v6。舊資料保留，新請求與ID有追溯映射，不能宣稱與舊保留題bytes相同。完整版本與問題歷程見[白話紀錄](analysis/訓練版本與問題處理白話紀錄.md)。Colab 入口與限制見 [模型說明](model/README.md)；本次新增Shopware語言清單與context切換的HTTP證據；1098筆分類資料本身仍offline。

## 現行範圍

| 平台 | 操作數 | 參數文件 |
|---|---:|---|
| Bagisto | 21 | [用途與參數](analysis/selected-api-contracts/bagisto/API_parameters.md) |
| Shopware | 20 | [用途與參數](analysis/selected-api-contracts/shopware/API_parameters.md) |
| Sylius | 21 | [用途與參數](analysis/selected-api-contracts/sylius/API_parameters.md) |

共 62 操作：56 核心、6 流程支援。第一版類別為 normal、sqli、xss；CMDi 與 path_traversal 待合理情境審核後另立實驗。Medusa 是凍結模型後的外部測試與 Demo 平台。

## 閱讀順序

1. [現行 API 索引](analysis/selected-apis.md)：完整 62 操作與實際採用的契約。
2. [實施計畫與正常流程](analysis/api-extension/plan.md)：版本條件、資料收集與 Demo。
3. [來源與採用狀態](../API_文件與採用範圍.md)：區分規格快照、固定實例與實測結果。
4. [資料規則](analysis/data-plan.md)、[特徵比較](analysis/feature-plan.md)、[驗證計畫](analysis/validation-plan.md)。

## 契約讀取

[active-api-manifest.json](analysis/api-extension/active-api-manifest.json) 是機器使用的採用清單。16 份遮罩結構修正版另存 contract-corrections；請依清單讀取，不能只掃描原目錄。

從專案根目錄執行 `python sentinel/scripts/active_api_contracts.py`，可唯讀核對 62 個操作的來源雜湊、操作內容、認證結構與參照。這不是參數文件完整性檢查、實機測試或模型效果驗證。

三份 API_parameters.md 已有人工修訂，不可用舊產生器整份覆寫。歷史重建工具與當時的保留／驗證報告已移入 [歷史區](analysis/history/README.md)，不能視為目前文件的通過證明。

Medusa 現行規格為 79 操作；舊 77 操作參數文件保留，差異見 [Medusa 文件狀態](../MSDSS_部署核對紀錄.md)。

當前v8用實機確認的英文／德文ID修正語言多樣性，Colab套件已更新；gateway模型仍為v7，需重新訓練後再替換。詳見[語言查核](analysis/Shopware語言ID查核.md)。

當前v9按原API文件、Bagisto／Sylius資料庫選項與參數含意多樣化，未部署應用或宣稱整批HTTP已執行；詳見[參數語義紀錄](analysis/參數語義與資料多樣性v9.md)。Colab已改v9，需重訓；gateway仍v7。

最新[依原API文件逐項復核32項](analysis/Medusa依原API文件逐項復核.md)，包含原文件快照、參數檢查、設定／資料庫／原生實作證據與HTTPS補測。未修改原API文件或模型。

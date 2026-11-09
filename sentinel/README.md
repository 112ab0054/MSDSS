# Sentinel

Sentinel 是本專案規劃中的 XGBoost 電商 API 請求分類模組。目前已有契約、API 參數文件與研究計畫，尚無正式訓練資料、模型或線上推論服務。

目前離線實驗為 small-api-v4：先分骨架群、再切集合；保持原始請求與特徵v5不變。Colab 入口與限制見 [模型說明](model/README.md)；本次沒有新增平台HTTP證據。

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

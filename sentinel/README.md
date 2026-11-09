# Sentinel：電商API三類偵測專題

XGBoost判斷normal／sqli／xss。訓練及測試平台為Bagisto、Shopware，獨立驗證為Sylius結合httpParamsDataset payload；Medusa供展示，不加入訓練資料。

## 當前版本

- 唯一保留的資料集：[small-api-v9](dataset/small-api-v9/README.md)，1098筆；train702、test150、validation150、challenge96。離線候選，不冒稱全部已實機執行。
- 訓練入口：[model README](model/README.md)、[Colab Notebook](model/msdss訓練.ipynb)與model/dataset.zip。ZIP資料與v9一致，已按當前程式重新打包並驗證。
- 現用完整模型：gateway/model/，使用者Colab v9、feature v6、input v3、2402維。模型與原始請求未因清理而改動。
- 最新評估：[Colab v9結果](model/results/colab-v9-2026-11-09/)。分數只代表指定離線集合，不能當作未測API的真實防護率。
- 推論入口：[gateway README](gateway/README.md)。所有經過gateway的支援HTTP方法及路徑都分析，忙碌排隊，觀察模式不封鎖；失敗或未載入模型會記錄並轉送。
- Medusa參考API已還原原77項，保留密碼重設請求；清單只供文件／平台驗證，不限制gateway。當前60成功、1部分成功、7前置不足、9功能／版本差異。[還原與真實接線證據](analysis/Medusa驗證與展示.md)。

## 目錄

| 目錄 | 用途 |
| --- | --- |
| model/ | 最新訓練、推論、評估、資料檢查、Colab打包與測試 |
| dataset/small-api-v9/ | 最新CSV、分組目錄、語義規則、資料來源與授權 |
| gateway/ | API轉送、模型分析、完整現用模型及部署說明 |
| local-platforms/ | 本機平台工具與真實HTTP證據；.runtime私有內容忽略Git |
| analysis/selected-api-contracts/ | Bagisto／Shopware／Sylius三份參數文件 |
| analysis/api-contracts/ | 原始規格來源 |
| analysis/ | 目前專題狀態、研究方法、驗證與歷程說明 |

2026-11-10已清除本機舊資料v1～v8、歷史模型包、重複輸出與舊版專用診斷。必要API快照、原始HTTP證據、解析器及授權仍保留，舊檔可從Git歷史還原。清理與全路徑gateway變更尚未提交／推送到隊友repo。

請先讀[PROJECT_CONTEXT](analysis/PROJECT_CONTEXT.md)了解目前狀態，歷史原因見[白話紀錄](analysis/訓練版本與問題處理白話紀錄.md)。不要把歷史文字中的舊目錄當成目前仍存在的資料版本。

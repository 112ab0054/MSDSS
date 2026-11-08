# MSDSS 目前專案狀態

更新日期：2026-11-08。此檔是工作摘要，不是 App 全域記憶或完整聊天匯出。

- 程式碼位置：C:/Users/USER/Downloads/MSDSS。工具預設 cwd 可能仍是 Documents/ChatGPT/msdss，請明確指定工作目錄。
- 三平台候選範圍共 62 操作：Bagisto 21、Shopware 20、Sylius 21；第一版 normal、sqli、xss。
- Medusa 程式固定 2.22.4，bundled Store 規格 info.version=2.22.3，共 79 操作。Medusa 是凍結模型後的外部測試與 Demo。
- 現行範圍見 selected-apis.md 與 api-extension/active-api-manifest.json。16 份修正版另存 contract-corrections；讀取時依清單選用。
- 三份 API_parameters.md 已經人工修訂，包含 Shopware 原第 16、18、20、21 節（移除 gateway 並重編號後為第 15、17、19、20 節）的局部補正；不得使用歷史產生器整份覆寫。API 標題、用途、參數、說明與可輸入值的後續變更，只處理使用者指定範圍並比對差異。
- 序列化方式與拆開傳送不顯示於三份參數文件，原始 OpenAPI 的 style／explode 欄位仍保留。
- 舊 45 操作審查及舊保留／驗證報告已歸檔；當時的雜湊與通過結果不代表目前人工修訂版。看 history/README.md。
- 尚未完成三平台固定實例、端到端正常流程、正式資料、模型訓練與跨平台效果驗證，不宣稱已部署有效防禦。
- 沙盒與 Mirage 由隊友負責，本次文件清理未修改其程式、部署或資料庫。

本次清理保留三份 API 參數文件、舊 Medusa 77 參數文件、原始規格及契約 JSON 的內容；更新現行索引與說明，舊產物移至歷史區。

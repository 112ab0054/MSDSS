# 選定 API 契約與參數文件

目前採用 62 個操作：Bagisto 21、Shopware 20、Sylius 21。

- [Bagisto](bagisto/README.md)、[Shopware](shopware/README.md)、[Sylius](sylius/README.md)：操作索引及參數文件。
- [機器採用清單](../api-extension/active-api-manifest.json)：實際讀取的 JSON 路徑與繼承認證要求。
- [既有契約補充](../api-extension/existing-api-supplements.md)：16 份另存修正版的原因。

原目錄保留的 16 份舊拆分檔有遮罩破壞 schema／security 的問題；機器採用清單改指向修正版，沒有覆寫原檔。其餘舊檔透過來源完整規格解析參照。片段不是獨立完整的 OpenAPI 文件。

三份 API_parameters.md 為目前人工維護的用途與參數文件。本次僅移除已停用的兩個操作章節並重編號，其餘參數內容保留。來源規格與實例驗證狀態見 [來源總表](../../../API_文件與採用範圍.md)；契約存在不代表已實測成功。

未採用的拆分 JSON 僅保留作來源，不應掃描目錄來推斷現行範圍；請以採用清單為準。

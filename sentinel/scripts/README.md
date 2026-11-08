# Sentinel 工具

目前可用的唯讀契約核對：

```sh
python sentinel/scripts/active_api_contracts.py
```

此工具依 active-api-manifest.json 讀取 64 操作，核對來源 SHA、操作內容、認證結構與參照。它不修改 API 參數文件，也不檢查實機流程或模型效果。

api_extension_schema.py 是契約解析共用程式，保留供讀取工具使用。舊 extend_api_scope.py 與 verify_api_extension.py 已移入歷史區，因其基準早於後續人工修訂，不能繼續用來覆寫或驗證現行文件。來源紀錄及舊輸入見 [歷史說明](../analysis/history/README.md)。

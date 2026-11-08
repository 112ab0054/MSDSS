# 原始 API 規格快照

這些檔案已用於候選端點篩選，不表示對應版本已部署成功。本次只更新索引，未重新下載或改動規格。既有紀錄記載擷取日期為 2026-11-08，精確時間與完整擷取證據未一律核對。

| 檔案 | 來源／固定紀錄 | info.version | SHA-256 |
|---|---|---|---|
| [bagisto/openapi-shop.json](bagisto/openapi-shop.json) | `bagisto/bagisto-api@97b202a4042c4429017ec0b8449cc856adc50323` | `2.4.10` | `f619df36bf29cde40aec76796b88d4690756fd9ccd4cc046b4c92ee458e78985` |
| [bagisto/openapi-admin.json](bagisto/openapi-admin.json) | `bagisto/bagisto-api@97b202a4042c4429017ec0b8449cc856adc50323` | `2.4.10` | `3198f11be70fffefa1e85de9aa76efdaf996559eeead3a41526fbc0aa962c4d5` |
| [shopware/storeapi.json](shopware/storeapi.json) | `shopware/store-api-reference@ce3a85fb3bb563357039054d4f6e72480f111884` | `6.7.9999999-dev` | `97d434d38bb669b9ffdc098fc68a29d2dcc8d23a28999e485e24ee1f17c338bb` |
| [shopware/adminapi.json](shopware/adminapi.json) | `shopware/admin-api-reference@355e6ebb337e9c7f214fc89c6ba3143c03095dcf` | `6.7.9999999-dev` | `9e271cc35f0c88ac7b9995d7298e990606d08ed0b15580ab25f1de7a9ff3e706` |
| [sylius/openapi-demo.json](sylius/openapi-demo.json) | `Sylius 公開 Demo；固定實例版本待確認` | `0.0.0` | `4ee96f0b2526d86170b626e00d78699a3d554f7d6008ffef17b6a17543439e1f` |
| [sylius/openapi-demo.yaml](sylius/openapi-demo.yaml) | `Sylius 公開 Demo；固定實例版本待確認` | `0.0.0` | `6242d0cd17c9036c0744e8a63132d7af31a2ea3f49d91350f96c01894d865061` |

## 已記錄的來源

- [Bagisto Shop](https://raw.githubusercontent.com/bagisto/bagisto-api/97b202a4042c4429017ec0b8449cc856adc50323/schema/generated/openapi-shop.json)、[Bagisto Admin](https://raw.githubusercontent.com/bagisto/bagisto-api/97b202a4042c4429017ec0b8449cc856adc50323/schema/generated/openapi-admin.json)。
- [Shopware Store](https://raw.githubusercontent.com/shopware/store-api-reference/ce3a85fb3bb563357039054d4f6e72480f111884/storeapi.json)、[Shopware Admin](https://raw.githubusercontent.com/shopware/admin-api-reference/355e6ebb337e9c7f214fc89c6ba3143c03095dcf/adminapi.json)。
- Sylius 既有擷取紀錄指向 [Demo JSON](https://v2.demo.sylius.com/api/v2/docs.jsonopenapi) 與 [Demo YAML](https://v2.demo.sylius.com/api/v2/docs.yamlopenapi)。此次未重新連線核對內容、下載時間或實例版本。

## 採用限制

Bagisto 規格版本仍須與實例及 API 套件對應；Shopware 目前是 dev 快照，須改用固定實例相符版本；Sylius 0.0.0 不能當作 framework 版本。正式收集前由固定實例重新核對／匯出並保存來源與雜湊。Admin 文件只留來源，不屬第一版顧客訓練範圍。

目前操作與修正版路徑見 [現行索引](../selected-apis.md) 及 [採用清單](../api-extension/active-api-manifest.json)。

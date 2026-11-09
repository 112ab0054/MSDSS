# API 文件導向離線資料 v3

主實驗 train/test/validation=450/150/150（60/20/20），另有96筆 challenge。所有集合三類等量；Medusa 不參與。

train/test 是相同來源家族、不同 payload 模板及 API 操作；challenge 保留未見的實體編碼／JS註解邊界與 SQL 結構語境。這是明確保留的語法／語境家族，不保證所有未知攻擊都涵蓋。validation 僅 Sylius，外部原文避開 v2 曾選的輸入，未依模型分數挑選。

四種位置每類分配相近，但各 API 僅使用文件宣告的位置。正常程式碼文字只填搜尋／備註等適合的自由文字欄，不填認證、語言、貨幣等欄來假造正常。完整參數覆蓋表含620個位置；620不是獨立請求數。

全部仍是離線生成請求，HTTP未執行。繼承 v2 的條件商品／自訂欄位／null關聯與歷史ID限制；攻擊值也可能不符型別／enum／長度。所有正常業務成功、儲存型／DOM行為及攻擊成功均未宣稱。不正規化原文，僅作JSON／URL傳輸序列化，憑證遮蔽。

metadata 中 historical_value_reference 只是歷史值來源，不是假造的 session；source_template_group、pair_group 和攻擊模板保留相依性。同家族可跨一般 train/test，不同模板不可跨；真實session與原文重複仍嚴格隔離。

固定種子選樣，不依 test/validation/challenge 成績調參。舊 v2 資料／v4 特徵及診斷保留。

```json
{
  "evaluation_protocol": "document-v3-seen-families-heldout-templates",
  "main_ratio": "60:20:20",
  "extra_challenge_is_not_part_of_ratio": true,
  "splits": {
    "train": {
      "rows": 450,
      "labels": {
        "normal": 150,
        "sqli": 150,
        "xss": 150
      },
      "platforms": {
        "bagisto": 141,
        "shopware": 309
      },
      "xss_unique_payloads": 20,
      "xss_families": {
        "xss.event": 30,
        "xss.js-string": 30,
        "xss.js-template": 30,
        "xss.script": 30,
        "xss.url": 30
      },
      "attack_locations_per_class": {
        "header": 38,
        "query": 37,
        "path": 37,
        "body": 38
      },
      "normal_literal_controls": 76
    },
    "test": {
      "rows": 150,
      "labels": {
        "normal": 50,
        "sqli": 50,
        "xss": 50
      },
      "platforms": {
        "bagisto": 84,
        "shopware": 66
      },
      "xss_unique_payloads": 10,
      "xss_families": {
        "xss.event": 10,
        "xss.js-string": 10,
        "xss.js-template": 10,
        "xss.script": 10,
        "xss.url": 10
      },
      "attack_locations_per_class": {
        "query": 12,
        "body": 13,
        "header": 13,
        "path": 12
      },
      "normal_literal_controls": 7
    },
    "validation": {
      "rows": 150,
      "labels": {
        "normal": 50,
        "sqli": 50,
        "xss": 50
      },
      "platforms": {
        "sylius": 150
      },
      "xss_unique_payloads": 24,
      "xss_families": {
        "external_unclassified": 50
      },
      "attack_locations_per_class": {
        "path": 12,
        "query": 12,
        "header": 13,
        "body": 13
      },
      "normal_literal_controls": 1
    },
    "challenge": {
      "rows": 96,
      "labels": {
        "normal": 32,
        "sqli": 32,
        "xss": 32
      },
      "platforms": {
        "bagisto": 36,
        "shopware": 60
      },
      "xss_unique_payloads": 8,
      "xss_families": {
        "xss.entity-encoded": 16,
        "xss.js-comment-boundary": 16
      },
      "attack_locations_per_class": {
        "header": 8,
        "query": 8,
        "path": 8,
        "body": 8
      },
      "normal_literal_controls": 15
    }
  },
  "parameter_document_sha256": {
    "sentinel/analysis/selected-api-contracts/bagisto/API_parameters.md": "783a8da3b6a93ae2fb0215260373e7e541998a642e16af5a6acde10a6a44758d",
    "sentinel/analysis/selected-api-contracts/shopware/API_parameters.md": "af6f3cadbf1e229c7db01bf12d7e43612e95bf74ef0381017bd2fdc42ca520f5",
    "sentinel/analysis/selected-api-contracts/sylius/API_parameters.md": "09684354ddaec52ec4f77c0a0bbcc5d1847ed6cb0f697e8df2ba2dac05dd2179"
  },
  "document_fields": 620,
  "api_operations": 62,
  "external_source": {
    "commit": "926670a710283f87c05b554680facf3f9530548c",
    "url": "https://raw.githubusercontent.com/Morzeux/HttpParamsDataset/926670a710283f87c05b554680facf3f9530548c/payload_full.csv",
    "sha256": "a4e62ba13435ad3dd583c5790db2175629020fc41c56e1b26baa02a9ae45f03d",
    "excluded_previous_external_values": 17,
    "selection": "seeded 24 per class; <=256 chars; no controls; no score-based filtering"
  },
  "http_executed": 0,
  "medusa_included": false,
  "source_generators_sha256": {
    "build_xss_v3.py": "5619b465bd8495be53a8d29118a2e08c543e511d5ea3c09807ae3a8c0c5a0967",
    "build_small_dataset.py": "27c3ce9f3493596b5d4f0c3d48797d55dd49c7488ceef2b4ec70b6bd2b508c8b"
  },
  "baseline_csv_sha256": {
    "train": "9962d26f0d99d3389d500eff1580c817dc87890718af3a7ff2fc231e1f8246ea",
    "test": "fd4eaeec2141b02182066f749816cd0d82b14b3f4ecd2841489c8e94b1f57dae",
    "validation": "5ab71efbb212a2773fc08417b8857a31d734c1305a060220e7d178ff2807701c"
  }
}
```

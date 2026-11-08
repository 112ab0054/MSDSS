# 小規模 API 候選 v2

420 筆候選，train/test/validation=252/84/84（60/20/20），各集合 normal/sqli/xss 等量。這個比例是方便檢查的小版本設計，不是跨平台評估的強制比例，也不是有效性的證明。

train/test 只用 Bagisto＋Shopware，操作及本地攻擊家族不跨集合；validation 僅 Sylius，payload 使用固定外部來源。Medusa 不納入。來源及切分欄位只在 metadata，不作模型輸入。

物件已依三份文件、原始 schema 與既有正常 HTTP 證據補形狀／值。憑證仍遮蔽，正常 ID 是歷史證據原值，不能推定目前仍有效。複合商品的結構範例不代表屬性／組合／預約種子已建立。全部候選未新送出、未核准訓練。

欄位細節見 field-coverage.csv，待辦與規格差異另見完成紀錄.md；舊 small-api-v1 保留供對照。

```json
{
  "splits": {
    "train": {
      "rows": 252,
      "labels": {
        "normal": 84,
        "sqli": 84,
        "xss": 84
      }
    },
    "test": {
      "rows": 84,
      "labels": {
        "normal": 28,
        "sqli": 28,
        "xss": 28
      }
    },
    "validation": {
      "rows": 84,
      "labels": {
        "normal": 28,
        "sqli": 28,
        "xss": 28
      }
    }
  },
  "ratio": "60:20:20",
  "labels_balanced_within_each_split": true,
  "document_fields": 620,
  "field_status": {
    "憑證安全遮蔽": 82,
    "值已填；實機有效性待確認": 528,
    "條件商品種子待建立；結構已填": 6,
    "選填關聯 null 接受方式待實測": 2,
    "需實例定義自訂欄位": 1,
    "整個空本文是合法結構": 1
  },
  "live_binding_markers_remaining": 0,
  "http_executed": 0,
  "training_approved": 0,
  "medusa_included": false,
  "parameter_document_sha256": {
    "sentinel/analysis/selected-api-contracts/bagisto/API_parameters.md": "aec73657e07b82a0bfa32016655665b5a2aed457c85af784b625c2bde07968a9",
    "sentinel/analysis/selected-api-contracts/shopware/API_parameters.md": "af6f3cadbf1e229c7db01bf12d7e43612e95bf74ef0381017bd2fdc42ca520f5",
    "sentinel/analysis/selected-api-contracts/sylius/API_parameters.md": "09684354ddaec52ec4f77c0a0bbcc5d1847ed6cb0f697e8df2ba2dac05dd2179"
  },
  "historical_evidence_sha256": {
    "sentinel/local-platforms/reports/bagisto-06da5b920937474aa5682afece8e65e0.json": "c1e99b6408739e6932cddb151d1edbf1c2a4b5b70b5c5dbc6372edd6ca7401f0",
    "sentinel/local-platforms/reports/bagisto-67146e3f4ed54ddf9df9c299128fdfb2.json": "6e1afda3397653c988355467555cc83d82a685dbec0906c6cfde95254f747ad9",
    "sentinel/local-platforms/reports/shopware-169394414b8a4d5180f8b5859fa77dce.json": "1733742012c7598185bd4e19100a477ee29506d6fc019a59c61c0ea754bb11f6",
    "sentinel/local-platforms/reports/shopware-32c3c4c9f50644a993ede3c43d5debc2.json": "93e151c24095b573213f78bca5a7671185f2cec294453c6863971e33027c5213",
    "sentinel/local-platforms/reports/sylius-24210669ab954772890b8bfb2d54a449.json": "6a55a45414b83bcd6df8fdde31801c26f62bbefd07ec5e50ca8ed5d550448cbf"
  },
  "historical_session_sources": {
    "train/bagisto": "sentinel/local-platforms/reports/bagisto-06da5b920937474aa5682afece8e65e0.json",
    "test/bagisto": "sentinel/local-platforms/reports/bagisto-67146e3f4ed54ddf9df9c299128fdfb2.json",
    "train/shopware": "sentinel/local-platforms/reports/shopware-169394414b8a4d5180f8b5859fa77dce.json",
    "test/shopware": "sentinel/local-platforms/reports/shopware-32c3c4c9f50644a993ede3c43d5debc2.json",
    "validation/sylius": "sentinel/local-platforms/reports/sylius-24210669ab954772890b8bfb2d54a449.json"
  },
  "external_source": {
    "repository": "https://github.com/Morzeux/HttpParamsDataset",
    "commit": "926670a710283f87c05b554680facf3f9530548c",
    "url": "https://raw.githubusercontent.com/Morzeux/HttpParamsDataset/926670a710283f87c05b554680facf3f9530548c/payload_full.csv",
    "sha256": "a4e62ba13435ad3dd583c5790db2175629020fc41c56e1b26baa02a9ae45f03d",
    "source_rows": 31067,
    "license": "MIT",
    "sampling": "seeded shuffle; max 256 characters; no control characters; 8 per class",
    "excluded_attack_types": [
      "cmdi",
      "path-traversal"
    ]
  }
}
```

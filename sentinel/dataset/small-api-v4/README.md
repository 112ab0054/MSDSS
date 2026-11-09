# API 文件導向離線資料 v4：骨架分組

train/test/validation=450/150/150（60/20/20），另有96筆 challenge。三類等量，62個 API、620個文件欄位位置。
Bagisto/Shopware 用於 train/test；Sylius 僅 validation，結合固定版本 httpParamsDataset 原文；Medusa 不參與。
全部是離線候選，HTTP 未執行，不能宣稱平台流程或攻擊成功。繼承 v2 的歷史ID與條件商品限制。

先對所有本地／外部攻擊建立骨架關聯，取連通群後才分配集合。字串、數字、console 輸出函式變體、
大小寫、常見百分比／HTML實體／JS跳脫包裝只在輔助分析視圖合併；原始請求與模型輸入不正規化。
同類同家族原文相似度達0.90也保守合併。這是片段語法規則，不是完整 SQL/JS AST 或所有語意等價的證明。
跨家族／跨平台相同骨架也合併。skeleton-catalog.csv 列出原始來源、簽章、分配與排除原因；不進入模型。

外部骨架優先保留 validation；重疊本地值排除，不移動 Sylius 至訓練。
原 challenge 的骨架及其本地兄弟全部保留 challenge；其餘骨架依固定雜湊排序約3:1分 train/test，
不依模型分數選資料。challenge 現為保留語境群，不能宣稱所有家族／編碼從未出現。
正常對照與兩類攻擊依 pair_group 同集合，API來源／模板關聯仍保留。骨架可跨多個配對，群數不是請求數。

沿用原有文件組裝器，保留全部文件基準與互斥 header 變體、四種輸入位置與正常自由文字控制。
參數可能不符 enum／型別，標籤表示來源意圖。保持特徵v5（2402維）與150棵、深度3、學習率0.05。
舊 small-api-v3 保留為近似變體基準，不能以舊97.33%代表未見骨架效果。

```json
{
  "evaluation_protocol": "document-v4-skeleton-disjoint",
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
      "xss_unique_payloads": 19,
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
      "xss_unique_payloads": 5,
      "xss_families": {
        "xss.js-template": 17,
        "xss.script": 16,
        "xss.url": 17
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
      "xss_unique_payloads": 14,
      "xss_families": {
        "xss.entity-encoded": 7,
        "xss.event": 6,
        "xss.js-comment-boundary": 7,
        "xss.script": 6,
        "xss.url": 6
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
    "build_xss_v3.py": "bea4b2be5ef1bdf6a18710ca89c5a9b6ed149c71e2f4af2463e01173a5f496b7",
    "build_small_dataset.py": "27c3ce9f3493596b5d4f0c3d48797d55dd49c7488ceef2b4ec70b6bd2b508c8b",
    "build_skeleton_v4.py": "608a143198a7d9879f32ed0782c3e77723d34321bbb8d4d37ac432c81a3a776e"
  },
  "baseline_csv_sha256": {
    "train": "9962d26f0d99d3389d500eff1580c817dc87890718af3a7ff2fc231e1f8246ea",
    "test": "fd4eaeec2141b02182066f749816cd0d82b14b3f4ecd2841489c8e94b1f57dae",
    "validation": "5ab71efbb212a2773fc08417b8857a31d734c1305a060220e7d178ff2807701c"
  },
  "skeleton_rule_version": 1,
  "skeleton_parser": {
    "id": "cpython-3.11.3-htmlparser-frozen-v1",
    "sha256": {
      "_skeleton_html_v1.py": "d50e7f0424cc76e88d6233a83654b2d456576a1980a8363b93955e9545763a1e",
      "_skeleton_markupbase_v1.py": "e7ec858cf543823191d8535e2f45945aa522bcfda7ce521a5fde04d618ee0e0a",
      "SKELETON-PYTHON-LICENSE.txt": "616fa565945eca2f0e0a5440b3973fed7d5291622b90849212077fe68e27dcb0"
    }
  },
  "skeleton_catalog_sha256": "fde7299ad55e2c8feb297d6e04da559522f978b77f98a73d1352bd9beefeb782",
  "skeleton_groups": {
    "train": {
      "xss": 12,
      "sqli": 7
    },
    "test": {
      "xss": 4,
      "sqli": 2
    },
    "validation": {
      "sqli": 20,
      "xss": 23
    },
    "challenge": {
      "xss": 8,
      "sqli": 4
    }
  },
  "excluded_local_overlaps": 0,
  "baseline": "small-api-v3 unchanged; raw-template/seen-family comparison only",
  "skeleton_source_sha256": "c46de4972ef09b21ec18342d0208b5429a23298d9db005d8fd7f6386104533c8"
}
```

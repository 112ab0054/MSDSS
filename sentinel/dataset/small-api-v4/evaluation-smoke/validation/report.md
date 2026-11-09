# 模型評估

候選試跑：True

以下數據只描述指定測試資料；不代表未測平台、未知家族或真實部署效果。

| 指標 | XGBoost | 永遠猜訓練集最多類別 |
|---|---:|---:|
| accuracy | 0.6400 | 0.3333 |
| balanced_accuracy | 0.6400 | 0.3333 |
| macro_precision | 0.6598 | 0.1111 |
| macro_recall | 0.6400 | 0.3333 |
| macro_f1 | 0.6299 | 0.1667 |
| weighted_f1 | 0.6299 | 0.1667 |
| micro_f1 | 0.6400 | 0.3333 |
| mcc | 0.4716 | 0.0000 |
| log_loss | 0.9965 | 24.0291 |
| multiclass_brier_score | 0.5238 | 1.3333 |
| normal_false_positive_rate | 0.1600 | 0.0000 |
| attack_detection_recall | 0.8100 | 0.0000 |
| attack_miss_rate | 0.1900 | 1.0000 |

## 各類結果

| 類別 | Precision | Recall | F1 | 筆數 |
|---|---:|---:|---:|---:|
| normal | 0.6885 | 0.8400 | 0.7568 | 50 |
| sqli | 0.7500 | 0.4200 | 0.5385 | 50 |
| xss | 0.5410 | 0.6600 | 0.5946 | 50 |

## 混淆矩陣

列＝真實，欄＝預測。

| 真實／預測 | normal | sqli | xss |
|---|---:|---:|---:|
| normal | 42 | 0 | 8 |
| sqli | 9 | 21 | 20 |
| xss | 10 | 7 | 33 |

## 資料與可信度

```json
{
  "audit": {
    "bundle_version": 1,
    "feature_version": 5,
    "request_input_version": 3,
    "labels": [
      "normal",
      "sqli",
      "xss"
    ],
    "header_names": [
      "accept-language",
      "authorization",
      "sw-access-key",
      "sw-context-source",
      "sw-context-token",
      "sw-include-search-info",
      "sw-include-seo-urls",
      "sw-language-id",
      "x-channel",
      "x-currency",
      "x-locale",
      "x-storefront-key"
    ],
    "feature_count": 2402,
    "feature_layout": {
      "version": 5,
      "hash_buckets_per_channel": 512,
      "ngram_sizes": [
        2,
        3,
        4,
        5
      ],
      "channels": [
        "query",
        "body",
        "path",
        "headers"
      ],
      "normalization": null,
      "lowercase_values": false,
      "vocabulary_fit": false,
      "extra_symbols": [
        "(",
        ")",
        "{",
        "}",
        "$",
        "`",
        "/",
        "\\",
        ":",
        "&",
        "#"
      ],
      "extra_patterns": [
        "\\b(?:alert|prompt|confirm|eval|Function|setTimeout|setInterval|void|console\\.info|String\\.fromCharCode)\\s*\\(",
        "\\b(?:document|window|location)\\s*\\.",
        "\\$\\{",
        "[\"\\'`]\\s*;",
        "</(?:script|textarea|style|title)",
        "%(?:3c|3e|22|27|28|29|3b|24|7b|7d)",
        "(?:%3c\\s*script|on\\w+%3d|javascript%3a)",
        "&#(?:x[0-9a-f]+|\\d+);|&(?:lt|gt|quot|apos);"
      ]
    },
    "header_document_sha256": {
      "sentinel/analysis/selected-api-contracts/bagisto/API_parameters.md": "783a8da3b6a93ae2fb0215260373e7e541998a642e16af5a6acde10a6a44758d",
      "sentinel/analysis/selected-api-contracts/shopware/API_parameters.md": "af6f3cadbf1e229c7db01bf12d7e43612e95bf74ef0381017bd2fdc42ca520f5",
      "sentinel/analysis/selected-api-contracts/sylius/API_parameters.md": "09684354ddaec52ec4f77c0a0bbcc5d1847ed6cb0f697e8df2ba2dac05dd2179"
    },
    "exploratory": true,
    "mode": "offline",
    "platform_http_verified": false,
    "python": "3.11.3",
    "packages": {
      "numpy": "2.3.5",
      "scikit-learn": "1.7.2",
      "xgboost": "3.1.2"
    },
    "parameters": {
      "objective": "multi:softprob",
      "base_score": null,
      "booster": null,
      "callbacks": null,
      "colsample_bylevel": null,
      "colsample_bynode": null,
      "colsample_bytree": null,
      "device": "cpu",
      "early_stopping_rounds": null,
      "enable_categorical": false,
      "eval_metric": "mlogloss",
      "feature_types": null,
      "feature_weights": null,
      "gamma": null,
      "grow_policy": null,
      "importance_type": null,
      "interaction_constraints": null,
      "learning_rate": 0.05,
      "max_bin": null,
      "max_cat_threshold": null,
      "max_cat_to_onehot": null,
      "max_delta_step": null,
      "max_depth": 3,
      "max_leaves": null,
      "min_child_weight": null,
      "missing": NaN,
      "monotone_constraints": null,
      "multi_strategy": null,
      "n_estimators": 150,
      "n_jobs": 2,
      "num_parallel_tree": null,
      "random_state": 42,
      "reg_alpha": null,
      "reg_lambda": null,
      "sampling_method": null,
      "scale_pos_weight": null,
      "subsample": null,
      "tree_method": "hist",
      "validate_parameters": null,
      "verbosity": null,
      "num_class": 3
    },
    "training_seconds": 2.881860800087452,
    "trees_selection": "predeclared_not_selected_by_holdout",
    "counts": {
      "train": {
        "normal": 150,
        "sqli": 150,
        "xss": 150
      },
      "test": {
        "normal": 50,
        "sqli": 50,
        "xss": 50
      },
      "validation": {
        "normal": 50,
        "sqli": 50,
        "xss": 50
      },
      "challenge": {
        "normal": 32,
        "sqli": 32,
        "xss": 32
      }
    },
    "group_overlap": 0,
    "independent_groups": {
      "train": 1,
      "test": 1,
      "validation": 1,
      "challenge": 1
    },
    "attack_skeleton_groups": {
      "train": {
        "sqli": 7,
        "xss": 12
      },
      "test": {
        "sqli": 2,
        "xss": 4
      },
      "validation": {
        "sqli": 20,
        "xss": 23
      },
      "challenge": {
        "sqli": 4,
        "xss": 8
      }
    },
    "evaluation_protocols": [
      "document-v4-skeleton-disjoint"
    ],
    "identical_feature_vectors_shared": {
      "train/test": 0,
      "train/validation": 0,
      "train/challenge": 0,
      "test/validation": 0,
      "test/challenge": 0,
      "validation/challenge": 0
    },
    "data_sha256": {
      "train": "e224a8a29e61b57ef53bd78fc81ca1cb0dcb2825b100fbd85d72688caf027852",
      "test": "f94a79a4da2de0a652d12800f4c6a0846f27f3c85921bd304cd6d98844e81788",
      "validation": "6d8320a20065bded2de497cfe73c022a6550a2f5356068766a61f4f2580cf3c8",
      "challenge": "695514773ce22200c99945e8fd27b2638ff6df1ebe3ccdcb9c24dc7d6cab6376"
    },
    "source_sha256": {
      "train.py": "2fb0686b8e3ddc9f85163c160d32c6d45e695648555b33337da20ff5fb1c33ef",
      "training.py": "87a6cb49c062ea5dd9cbb40685439dd31a0170981984e42afda96ef861bea27e",
      "preflight.py": "936fcd287e08af66b711808758814aad073090ee17659cf7bd4792a8775bb190",
      "data_io.py": "72f3fed9a9e0ab18c3531293bf30df337a06f22d8417906667d81b68da39fb58",
      "evaluate.py": "25f0c3d4583a33dbf248909e63a3bbeff9fc5fb66569575d26c4811f3507985d",
      "features.py": "384dc78d1ae721f4583d87a6df01bdafb35868b7b8749f4e8955fd5777f55c97",
      "request_input.py": "417a93fad371c66a8f70b925a240ad93034a3dc688d6f3e2a5b2ee1387589675",
      "skeletons.py": "c46de4972ef09b21ec18342d0208b5429a23298d9db005d8fd7f6386104533c8"
    },
    "seed": 42,
    "platform": "Windows",
    "readiness": {
      "ready": true,
      "mode": "offline",
      "exploratory": true,
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
          "http_executed": 0,
          "observed_sessions": 0,
          "pair_groups": 150,
          "attack_skeleton_groups": {
            "sqli": 7,
            "xss": 12
          },
          "sha256": "e224a8a29e61b57ef53bd78fc81ca1cb0dcb2825b100fbd85d72688caf027852",
          "independent_groups": 1
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
          "http_executed": 0,
          "observed_sessions": 0,
          "pair_groups": 50,
          "attack_skeleton_groups": {
            "sqli": 2,
            "xss": 4
          },
          "sha256": "f94a79a4da2de0a652d12800f4c6a0846f27f3c85921bd304cd6d98844e81788",
          "independent_groups": 1
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
          "http_executed": 0,
          "observed_sessions": 0,
          "pair_groups": 50,
          "attack_skeleton_groups": {
            "sqli": 20,
            "xss": 23
          },
          "sha256": "6d8320a20065bded2de497cfe73c022a6550a2f5356068766a61f4f2580cf3c8",
          "independent_groups": 1
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
          "http_executed": 0,
          "observed_sessions": 0,
          "pair_groups": 32,
          "attack_skeleton_groups": {
            "sqli": 4,
            "xss": 8
          },
          "sha256": "695514773ce22200c99945e8fd27b2638ff6df1ebe3ccdcb9c24dc7d6cab6376",
          "independent_groups": 1
        }
      },
      "document_snapshots": {
        "sentinel/analysis/selected-api-contracts/bagisto/API_parameters.md": "not_available",
        "sentinel/analysis/selected-api-contracts/shopware/API_parameters.md": "not_available",
        "sentinel/analysis/selected-api-contracts/sylius/API_parameters.md": "not_available"
      },
      "errors": [],
      "warnings": [
        "離線生成資料：可評估分類器，但沒有完成平台 HTTP 實機驗證。群組數是相依關聯的合併結果，不等於真實購物流程數。"
      ],
      "note": "檢查通過僅代表目前程式的資格與分組條件通過，不代表模型有效。"
    },
    "evaluated_split": "validation",
    "latency_ms": {
      "median": 1.5994501300156116,
      "p95": 2.662374963983893
    }
  },
  "confidence_interval": {
    "available": false,
    "reason": "測試獨立群組少於 20，暫不報信賴區間。",
    "independent_groups": 1
  }
}
```

ROC-AUC、Average Precision 與逐類比例見 report.json；Average Precision 應對照該類比例解讀。
完整逐筆預測見 predictions.csv。沒有實作規則或其他學習器的比較，尚不能宣稱優於它們。

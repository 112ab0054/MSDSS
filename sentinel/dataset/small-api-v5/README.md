# v5：只補強訓練資料

train594（每類198），test150、Sylius validation150、challenge96原檔凍結，共990筆。三份保留CSV的所有bytes、ID、骨架、標籤不變；舊small-api-v4保留。比例不再是60/20/20，因為只增加train，不能假稱原比例。
新增48組正常／SQLi／XSS配對共144筆，四位置每類各12，依三份API文件選欄位；companyName只放公司名稱，教材字面內容只放搜尋／備註自由文字。新增攻擊依骨架與跨家族原文近似檢查避開全部既有攻擊；排除紀錄見candidate-decisions.csv。
全部仍是離線候選，HTTP=0、業務與攻擊成功未驗證；API型別／enum限制可能拒絕攻擊。沒有新造路徑或ID去填正常長路徑，這個涵蓋缺口仍存在。CASE／JS片段需相應可執行語境，標籤表示來源意圖。
只依已觀察到的錯誤類型策劃一次資料補強；保留集已被檢視，只能作探索性比較，不能宣稱最終泛化。沒有用新評估成績挑案例或調參。原文不正規化，特徵v5=2402維與固定150棵參數不變。Medusa不使用，Sylius只作外部驗證，外部來源與MIT授權維持不變。

```json
{
  "evaluation_protocol": "document-v4-skeleton-disjoint",
  "main_ratio": "594:150:150; holdouts frozen, not 60:20:20",
  "extra_challenge_is_not_part_of_ratio": true,
  "splits": {
    "train": {
      "rows": 594,
      "labels": {
        "normal": 198,
        "sqli": 198,
        "xss": 198
      },
      "platforms": {
        "bagisto": 195,
        "shopware": 399
      }
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
      }
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
      }
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
      }
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
    "build_train_v5.py": "045cabe9e637a42eff03238ac80b3aac9fc449f0e8e47ba64327626f0461ceaa",
    "build_xss_v3.py": "bea4b2be5ef1bdf6a18710ca89c5a9b6ed149c71e2f4af2463e01173a5f496b7",
    "build_small_dataset.py": "27c3ce9f3493596b5d4f0c3d48797d55dd49c7488ceef2b4ec70b6bd2b508c8b"
  },
  "baseline_csv_sha256": {
    "train": "e224a8a29e61b57ef53bd78fc81ca1cb0dcb2825b100fbd85d72688caf027852",
    "test": "f94a79a4da2de0a652d12800f4c6a0846f27f3c85921bd304cd6d98844e81788",
    "validation": "6d8320a20065bded2de497cfe73c022a6550a2f5356068766a61f4f2580cf3c8",
    "challenge": "695514773ce22200c99945e8fd27b2638ff6df1ebe3ccdcb9c24dc7d6cab6376"
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
  "skeleton_catalog_sha256": "ab176a26caeca72e5f8ea1c1cc0c2b0988a16e2cdd64a21a2552ab52ad7ced67",
  "skeleton_groups": {
    "train": {
      "xss": 35,
      "sqli": 31
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
  "skeleton_source_sha256": "c46de4972ef09b21ec18342d0208b5429a23298d9db005d8fd7f6386104533c8",
  "dataset_revision": "v5-train-augmentation",
  "frozen_holdout_sha256": {
    "test": "f94a79a4da2de0a652d12800f4c6a0846f27f3c85921bd304cd6d98844e81788",
    "validation": "6d8320a20065bded2de497cfe73c022a6550a2f5356068766a61f4f2580cf3c8",
    "challenge": "695514773ce22200c99945e8fd27b2638ff6df1ebe3ccdcb9c24dc7d6cab6376"
  },
  "augmentation": {
    "triples": 48,
    "rows": 144,
    "per_class": 48,
    "platforms": {
      "shopware": 90,
      "bagisto": 54
    },
    "new_payloads_per_class": {
      "sqli": 24,
      "xss": 24
    },
    "decisions": {
      "new_training_skeleton": 48
    },
    "source": "locally curated SQL/JS fragments and documented normal contrast; not new external corpus",
    "evaluation_already_inspected": true,
    "normal_long_path_gap": "no fabricated routes/IDs; still unresolved"
  }
}
```

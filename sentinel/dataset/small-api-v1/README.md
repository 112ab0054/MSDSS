# 小規模 API 文件導向候選資料集

這是新候選版本，不覆寫舊資料；不是已完成實機採集或可正式訓練的資料。

- train.csv／test.csv：Bagisto＋Shopware；每平台保留 4 個 API 作測試，操作不跨集合。
- validation.csv：僅 Sylius；攻擊與額外正常輸入來自固定 commit 的 httpParamsDataset。
- Medusa 不參與任何集合。來源標記只放 metadata，不是模型輸入。
- 每個 API 的文件欄位全部列在 field-coverage.csv，包含 Header、Query、Path、巢狀 Body。
- API 沒有的參數位置不硬加；sw-context-token／sw-context-source 分成互斥候選，session 方案須綁 Cookie。
- 原文保留，不做大小寫、ID、空白、編碼正規化；raw 欄是新生成的傳輸文字，不冒充歷史封包。
- 憑證只保留 [REDACTED]；${LIVE:...} 代表尚缺實例值，不是假造可用 ID。
- 文件未展開的物件保留 {}，陣列成員可能待綁定；合成值、篩選組合、認證、業務限制均未驗證。
- Query 物件使用括號式欄位；空物件／空陣列仍為可見骨架，序列化和 API 接受方式待實機核對，不能宣稱其結構已填完。
- 外部 norm 僅表示原資料標籤，不代表一定符合電商欄位格式；攻擊意圖不代表漏洞成立。
- 每 API 每個可變動位置只選一欄放 payload，控制總量；不表示每欄都已測攻擊／每種家族全覆蓋。
- 外部 payload 全檔與本地攻擊原文做精確排重；不宣稱語意或近似家族完全獨立。
- 訓練／測試家族不同，這是較難的初步設計；各平台比例與 API 難度未配平，不能據此報告效果。
- 不調參使用 test 或 validation；實際採集時另建獨立 session 並維持同流程／同來源家族分組。
- 尚需：本機綁定、正常流程業務斷言、逐筆 HTTP 證據、格式／標籤審核，再匯出正式資料。

目前統計：

```json
{
  "splits": {
    "train": {
      "rows": 165,
      "labels": {
        "normal": 39,
        "sqli": 63,
        "xss": 63
      },
      "platforms": [
        "bagisto",
        "shopware"
      ]
    },
    "test": {
      "rows": 38,
      "labels": {
        "normal": 8,
        "sqli": 15,
        "xss": 15
      },
      "platforms": [
        "bagisto",
        "shopware"
      ]
    },
    "validation": {
      "rows": 118,
      "labels": {
        "normal": 30,
        "sqli": 44,
        "xss": 44
      },
      "platforms": [
        "sylius"
      ]
    }
  },
  "api_operations": 62,
  "document_fields": 620,
  "fields_present_in_candidates": 620,
  "field_binding_status": {
    "已填候選值；未實測": 397,
    "待綁定憑證／實例值": 180,
    "結構待依實例補充": 43
  },
  "http_executed": 0,
  "training_approved": 0,
  "parameter_document_sha256": {
    "sentinel/analysis/selected-api-contracts/bagisto/API_parameters.md": "aec73657e07b82a0bfa32016655665b5a2aed457c85af784b625c2bde07968a9",
    "sentinel/analysis/selected-api-contracts/shopware/API_parameters.md": "af6f3cadbf1e229c7db01bf12d7e43612e95bf74ef0381017bd2fdc42ca520f5",
    "sentinel/analysis/selected-api-contracts/sylius/API_parameters.md": "09684354ddaec52ec4f77c0a0bbcc5d1847ed6cb0f697e8df2ba2dac05dd2179"
  },
  "scenario_catalog_sha256": "cb345e1f505e9fa4734ee4741e7c02e0a075d2001092aaa70075dbe366a8e25b",
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
  },
  "split_rule": "operation-disjoint 4 held-out APIs per training platform; family-disjoint local attack catalog",
  "medusa_included": false,
  "normalization": "none; transport serialization only; credential values redacted"
}
```

重現：在專案根目錄執行 `python -B sentinel/dataset/build_small_dataset.py --output <新的輸出目錄>`。產生器只下載固定來源並寫候選，不啟動平台、不發送攻擊、不訓練模型。

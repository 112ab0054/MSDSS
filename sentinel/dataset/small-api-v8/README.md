# v8：實機語言 ID 多樣性

依目前本機 Shopware 語言清單與 context 語言鏈驗證，平均分配有效 ID。每組 normal／SQLi／XSS 使用相同背景語言，保留原攻擊文字、標籤、集合與骨架。原 v7 保留；新舊 sample ID 有映射。

語言 API 成功不代表 1098 筆資料已全部送出；資料仍是 offline。舊模型未自動換成新模型，需用新版 dataset.zip 重新訓練。

{
  "inventory_sha256": "fe056420ce0e5a0e0d92f7b0ae6735729774c09073a27a616fd47db9b256cec6",
  "accepted_ids": [
    "01a162e6e938738db9be38797c416637",
    "2fbb5fe2e29a4d70aa5854ce7ce3e20b"
  ],
  "normal_header_counts": {
    "train": {
      "01a162e6e938738db9be38797c416637": 42,
      "2fbb5fe2e29a4d70aa5854ce7ce3e20b": 41
    },
    "test": {
      "01a162e6e938738db9be38797c416637": 7,
      "2fbb5fe2e29a4d70aa5854ce7ce3e20b": 6
    },
    "validation": {},
    "challenge": {
      "01a162e6e938738db9be38797c416637": 8,
      "2fbb5fe2e29a4d70aa5854ce7ce3e20b": 7
    }
  },
  "changed_request_rows": 145,
  "allocation": "round-robin within split, same language per normal/sqli/xss triple; attack on language preserved",
  "only_language_requests_http_verified": true,
  "dataset_requests_http_verified": false
}

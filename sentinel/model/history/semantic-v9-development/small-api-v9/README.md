# v9：按參數含意產生多樣化文字

原v8保留。1098筆、標籤、集合、骨架與攻擊原文不變，正常控制及配對背景明確修正，原文不是在推論時正規化。

Bagisto資料庫只有en，不能捏造其他已建立語言。Sylius使用資料庫與文件交集的8種語言，現有通路僅en_US，按使用者指定作資料庫目錄範圍的離線訓練，沒有假稱這些語言已在通路HTTP驗收。國家與州省使用資料庫選項；地址、人名、公司、電話與稅號文字都是合成示例，不表示真實聯絡或稅籍有效。

自由字串按含意改寫，保留原正常字面程式碼對照及外部normal內容。只有1或2筆的欄位最多只有1或2個不同值，不為湊多樣性複製資料。固定值、憑證、實例ID與結構化值另列原因。620個文件位置皆有狀態；整批仍offline，需重新訓練，不沿用舊版模型分數或自動替換gateway。

{
  "field_changes": 1036,
  "document_positions": 620,
  "input_rows_changed": 794,
  "database_sources": [
    {
      "path": "sentinel/local-platforms/reports/bagisto-database-catalog.json",
      "sha256": "80a5fde55d26e2aa42cca9ca8cf703867c6582d91721ea75af541da79316ab47"
    },
    {
      "path": "sentinel/local-platforms/reports/sylius-database-catalog.json",
      "sha256": "1ea658cf6c3788b6610b3add6e3293ed33823aee1192bdf7cc5851d02afa3dc5"
    },
    {
      "path": "sentinel/local-platforms/reports/shopware-057a8b6d60664a2d9651c52498dc172d.json",
      "sha256": "25c1e68af3c26be874b739ef22ceebdc80c72ea12d5bcb1bbfe89c405acc5174"
    },
    {
      "path": "sentinel/local-platforms/reports/shopware-169394414b8a4d5180f8b5859fa77dce.json",
      "sha256": "1733742012c7598185bd4e19100a477ee29506d6fc019a59c61c0ea754bb11f6"
    },
    {
      "path": "sentinel/local-platforms/reports/shopware-32c3c4c9f50644a993ede3c43d5debc2.json",
      "sha256": "93e151c24095b573213f78bca5a7671185f2cec294453c6863971e33027c5213"
    },
    {
      "path": "sentinel/local-platforms/reports/shopware-e44f75f68dab45538045a43a66b6933a.json",
      "sha256": "6993e33232280a5d76029eef2b88567368c9ce3fd681f4e7ee0d08d05eaee03e"
    }
  ],
  "language_scope": "database catalogue as requested; Sylius channel assignments remain en_US; no HTTP verification",
  "address_scope": "synthetic coherent country/city/postcode/state profiles; not verified deliverability",
  "generator_sha256": "c9783362b04f5e11e54e6fd254b4077ece5541f0395aa7ea7302d6729aa6d849",
  "catalog_sha256": {
    "bagisto": "80a5fde55d26e2aa42cca9ca8cf703867c6582d91721ea75af541da79316ab47",
    "sylius": "1ea658cf6c3788b6610b3add6e3293ed33823aee1192bdf7cc5851d02afa3dc5"
  },
  "preserved_source_controls": 160,
  "http_executed": 0
}

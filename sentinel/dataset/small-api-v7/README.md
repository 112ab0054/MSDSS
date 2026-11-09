# v7：依文件修正正常值

原v6閱讀版保留。修正正常控制後重新嵌入完全相同的攻擊payload；標籤、集合與骨架不變，ID另存新舊映射。原始輸入在新版本中是明確修正，不是偷偷正規化。

僅有歷史實測語言ID，Docker引擎未運作，未宣稱現在可用或所有業務已通。未知可選ID不捏造；文件分支不是實際欄位，未知或文件／固定版本規格矛盾的選填欄位另記省略原因。不能再宣稱620個位置全部在請求中同時出現。

{
  "normal_rows": 366,
  "before_rule_issues": 844,
  "after_rule_issues": 0,
  "field_changes": 723,
  "historical_evidence": [
    {
      "path": "sentinel/local-platforms/reports/bagisto-06da5b920937474aa5682afece8e65e0.json",
      "sha256": "c1e99b6408739e6932cddb151d1edbf1c2a4b5b70b5c5dbc6372edd6ca7401f0",
      "recorded_at": "2026-11-08T07:21:14.453549+00:00"
    },
    {
      "path": "sentinel/local-platforms/reports/bagisto-67146e3f4ed54ddf9df9c299128fdfb2.json",
      "sha256": "6e1afda3397653c988355467555cc83d82a685dbec0906c6cfde95254f747ad9",
      "recorded_at": "2026-11-08T07:21:07.094212+00:00"
    },
    {
      "path": "sentinel/local-platforms/reports/bagisto-91b4ce087a474bf6b625d14d71c3dde8.json",
      "sha256": "1d3594a292dc819aee9f4b8136bfe9868e0527dd22fb1c3f24b80027e2ab5ef4",
      "recorded_at": "2026-11-08T19:43:16.178499+00:00"
    },
    {
      "path": "sentinel/local-platforms/reports/shopware-057a8b6d60664a2d9651c52498dc172d.json",
      "sha256": "25c1e68af3c26be874b739ef22ceebdc80c72ea12d5bcb1bbfe89c405acc5174",
      "recorded_at": "2026-11-08T19:50:27.125707+00:00"
    },
    {
      "path": "sentinel/local-platforms/reports/shopware-169394414b8a4d5180f8b5859fa77dce.json",
      "sha256": "1733742012c7598185bd4e19100a477ee29506d6fc019a59c61c0ea754bb11f6",
      "recorded_at": "2026-11-08T08:41:08.787806+00:00"
    },
    {
      "path": "sentinel/local-platforms/reports/shopware-32c3c4c9f50644a993ede3c43d5debc2.json",
      "sha256": "93e151c24095b573213f78bca5a7671185f2cec294453c6863971e33027c5213",
      "recorded_at": "2026-11-08T02:38:22.735946+00:00"
    },
    {
      "path": "sentinel/local-platforms/reports/shopware-e44f75f68dab45538045a43a66b6933a.json",
      "sha256": "6993e33232280a5d76029eef2b88567368c9ce3fd681f4e7ee0d08d05eaee03e",
      "recorded_at": "2026-11-08T02:37:44.339943+00:00"
    },
    {
      "path": "sentinel/local-platforms/reports/sylius-0daa99cc36ad462db8dc5c14334c61e5.json",
      "sha256": "7161e19347722decb53d9accb54f79d4e4a07621cadca247da63e5a09dd3857d",
      "recorded_at": "2026-11-08T07:35:36.257104+00:00"
    },
    {
      "path": "sentinel/local-platforms/reports/sylius-24210669ab954772890b8bfb2d54a449.json",
      "sha256": "6a55a45414b83bcd6df8fdde31801c26f62bbefd07ec5e50ca8ed5d550448cbf",
      "recorded_at": "2026-11-08T07:37:23.904057+00:00"
    },
    {
      "path": "sentinel/local-platforms/reports/sylius-435109624adb4d909b907a9da7550277.json",
      "sha256": "df619d6a749d39a6d7e63aef3ec3ef109c715b0755914d47c1f6e53fdec38568",
      "recorded_at": "2026-11-08T20:00:35.802849+00:00"
    }
  ],
  "current_platform_rechecked": false,
  "language_ids_confirmed_in_history": [
    "2fbb5fe2e29a4d70aa5854ce7ce3e20b"
  ],
  "omitted_fields": [
    {
      "parameter": "items[].priceDefinition.type",
      "reason": "standard_product_uses_platform_price_omit_custom_definition",
      "normal_rows": 4
    },
    {
      "parameter": "countryStateId",
      "reason": "optional_state_id_unbound_omit_not_fake",
      "normal_rows": 15
    },
    {
      "parameter": "slots",
      "reason": "optional_identifier_or_sorting_not_bound_to_platform",
      "normal_rows": 49
    },
    {
      "parameter": "order",
      "reason": "optional_identifier_or_sorting_not_bound_to_platform",
      "normal_rows": 30
    },
    {
      "parameter": "reduce-aggregations",
      "reason": "optional_document_live_schema_disagreement_omit_flag",
      "normal_rows": 30
    },
    {
      "parameter": "no-aggregations",
      "reason": "optional_document_live_schema_disagreement_omit_flag",
      "normal_rows": 30
    },
    {
      "parameter": "only-aggregations",
      "reason": "optional_document_live_schema_disagreement_omit_flag",
      "normal_rows": 30
    },
    {
      "parameter": "productTaxons.taxon.code",
      "reason": "optional_identifier_or_sorting_not_bound_to_platform",
      "normal_rows": 5
    },
    {
      "parameter": "localeCode for order[translation.name]",
      "reason": "optional_identifier_or_sorting_not_bound_to_platform",
      "normal_rows": 5
    },
    {
      "parameter": "taxon",
      "reason": "optional_identifier_or_sorting_not_bound_to_platform",
      "normal_rows": 5
    },
    {
      "parameter": "association[typeCode]",
      "reason": "optional_identifier_or_sorting_not_bound_to_platform",
      "normal_rows": 5
    },
    {
      "parameter": "association[ownerCode]",
      "reason": "optional_identifier_or_sorting_not_bound_to_platform",
      "normal_rows": 5
    },
    {
      "parameter": "billingAddress〈anyOf分支2〉",
      "reason": "documentation_union_branch_is_not_a_wire_property",
      "normal_rows": 5
    },
    {
      "parameter": "shippingAddress〈anyOf分支2〉",
      "reason": "documentation_union_branch_is_not_a_wire_property",
      "normal_rows": 5
    }
  ],
  "sensitive_values_redacted": true,
  "still_requires_live_business_validation": true
}

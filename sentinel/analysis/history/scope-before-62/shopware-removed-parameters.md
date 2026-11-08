## 02. 呼叫結帳關卡 API

`GET /checkout/gateway`

**operationId：** checkoutGateway
**來源檔案：** get-checkout-gateway.json

**API 涵義：** 回傳結帳關卡處理結果。

| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |
|---|---|---|---|---|---|
| header | sw-access-key | 依認證組合 | string | Shopware 銷售通路存取金鑰；屬敏感資料，不應寫入模型或一般日誌。 | 實際值由部署環境提供。 |
| query | orderId | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | 參數 `orderId` 的業務涵義未在契約中詳細說明；僅依契約型別與欄位名稱記錄。 |
| header | sw-language-id | 選填 | string | 正規表達式：`^[0-9a-f]{32}$` | Shopware 回應內容使用的語言識別值。 |
| header | sw-context-source | 選填 | string | 固定值：`session` | Shopware 請求情境的來源識別值。 |

### 回應狀態

| 狀態碼 | 回應說明 |
|---|---|
| 200 | 此狀態表示 API 回應了「Checkout gateway response」結果。 |
| 401 | 缺少 `sw-access-key` header。 |

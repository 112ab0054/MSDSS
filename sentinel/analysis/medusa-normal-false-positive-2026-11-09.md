# Medusa正常查詢誤報：Accept萬用媒體型別與SQL註解特徵混淆

## 重現與根因

固定現有gateway模型SHA f191cdc17704a9e20291c674e03f0920b5236ca17a621a1585c90f268e2a6e77，不調門檻、不重訓、未送HTTP。
離線組出HTTPX預設headers，經真正gateway.model_request與Predictor執行，重現 `query=cotton` 的normal30.2256%／sqli56.7988%／xss12.9756%。此前原紀錄沒有完整headers，單看URL不能唯一決定結果；現在另保存可重現的完整遮蔽副本與環境profile。

現行features.PATTERNS中的SQL註解正則 `--|/\*|\*/`，對所有非敏感header聚合文字套用。在合法 `Accept: */*` 或 `Accept: application/*` 內會命中 `/*`。這不是SQL注入內容，卻使headers.aggregate.sql_comment變成1。原探針此格對SQLi減normal的TreeSHAP原始分數貢獻約+2.269，是該次最大正向項。hash桶亦有作用，不能宣稱所有誤報只有這個原因。

## 只改Accept的受控比較

以下保持 `GET /store/products?q=cotton`、其他HTTPX預設headers、空本文、模型與argmax全部相同，只改Accept。

| Accept | normal分數 | SQLi分數 | XSS分數 | 結果 |
|---|---:|---:|---:|---|
| `*/*` |33.9425%|53.7731%|12.2844%|SQLi|
| `application/json` |68.4350%|6.7971%|24.7678%|normal|
| `application/*` |33.9425%|53.7731%|12.2844%|SQLi|

這驗證了合法header值能觸發誤報。不是建議為了讓Demo顯示正常而偷偷改瀏覽器header，也不是把Accept整個移除或不分析。正式瀏覽器仍可能傳萬用媒體型別，應照原樣偵測與轉送。

## API規格差異

本專案固定Medusa規格 backend/static/openapi/store.yaml 的GET /store/products（15703行開始）使用搜尋參數`q`、分頁`limit/offset`，不是先前探針的`query/page`。規格也要求x-publishable-api-key。

改成正確q參數後，HTTPX預設Accept仍誤報，所以錯參數不是唯一原因。本次API文件header profile只放[REDACTED]作模型副本，不是真金鑰，未宣稱HTTP成功、商品存在或正常業務驗收。既有API文件和原接線紀錄不覆寫；差異另存本檔。

## 修正方向與Demo安排

1. 目前維持只告警不封鎖。模型預測SQLi要照實顯示為「模型判定」，不能說已確認攻擊；保留三類未校準分數與離線標記。
2. 修正訓練資料的HTTP傳輸環境涵蓋：在Bagisto／Shopware三類請求均加入一致的合法Accept萬用值、瀏覽器／HTTPX一般headers，避免把某客戶端headers與單一標籤綁定。原始請求不正規化、不刪header；Medusa請求不放進訓練。
3. 若改特徵，應辨識Accept的合法媒體型別語意，避免把其中`/*`直接當SQL註解。需提升特徵版本、重訓並重新產生整套inference；不能只改gateway的features.py或重寫manifest假裝相容。異常值與其他header仍保留分析。
4. 不能只靠這筆誤報把門檻提高到0.8／0.9；這會改變漏判率，需在train內另建開發資料驗證。保留原模型與當前結果，避免與正式修正後模型混用。
5. 真實Medusa正常流程仍須從網站擷取與驗證。本次少量探針已作診斷使用，不能把它們宣稱為完全未接觸的最終評估題。

本輪完成的是可重現診斷，沒有修改訓練／推論規則、權重、gateway行為或資料集，也不聲稱已修復誤報。證據在sentinel/gateway/normal-probe-diagnosis-2026-11-09/controlled/audit.json與score-contributions.csv；程式sentinel/gateway/diagnose_normal_probe.py可對新目錄重跑。

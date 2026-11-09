# 2026-11-09：骨架分組資料 v4

使用者同意先合併近似模板再分集合。本次在 Documents/GitHub/MSDSS 實作，沒有修改三份 API_parameters.md、Medusa、Mirage、根目錄 compose 或平台資料庫，沒有新增平台 HTTP 請求。

## 修正的問題與實際例子

v3 檢查不同原文與 template_id，仍可讓只換常數的攻擊跨集合。使用者的 test accuracy 97.33% 是該版已見家族／近似變體試跑結果，不能解讀為未見骨架辨識能力。

新版全域目錄中：

| 原文 | 原本 v3 | v4分配 | 原因 |
|---|---|---|---|
| `' AND SLEEP(0)=0 -- ` | train | train | 同 SLEEP 比較骨架 |
| `' AND SLEEP(0.05)=0 -- ` | test | train | 只改數字，不當作獨立考題 |
| `<script>console.info("catalog")</script>` | train | challenge | 同輸出呼叫骨架 |
| `<script>console.log("product")</script>` | test | challenge | 別名、字串變體與上一列同群 |
| `&#60;script&#62;console.info("encoded")&#60;/script&#62;` | challenge | challenge | 編碼兄弟帶動整群留在challenge |

詳見 ../dataset/small-api-v4/skeleton-catalog.csv。骨架群是一組不同原文，不是單筆HTTP、攻擊成功證據或真實session。

## 分組與分配規則

1. 固定版本的全部本地攻擊和外部24筆／類攻擊先一起建目錄，早於模型fit／評估。
2. 分組視圖最多三輪解百分比、HTML實體、JS\u／\x跳脫；大小寫、字串數字常數與console輸出別名保守合併。HTML依標籤、屬性與內嵌JS片段，SQL／JS依token結構產生簽章。同類同家族且視圖字串相似度至少0.90再補近似邊，取連通群。
3. 外部群保留Sylius validation，重疊本地值排除；不將外部驗證資料改成訓練資料。本次排除數0，仍保留規則避免未來新增資料洩漏。
4. 原challenge群與其本地兄弟全部保留challenge；其他群依固定雜湊排序，約3:1分train/test，至少各一群，不用評估分數選資料。
5. 使用三份API文件原有的組裝器與API分配，把正常／SQLi／XSS三筆控制配對留在同集合。配對、來源模板、真實session／完全重複與骨架關聯共同檢查。
6. preflight重算全目錄與實際樣本，不只信任skeleton_group_id；缺規則、目錄、錯SHA、錯簽章或跨集合骨架都拒絕。骨架欄位不進模型特徵。

這是版本化的保守片段語法與近似規則，**不是完整SQL／JavaScript AST解析器，也不是所有語意等價的證明**。可能把不同片段保守合併，也可能漏掉高階改寫。後續新增payload須先重建目錄、檢視分組再凍結評估，不能只換ID。

## 資料與固定條件

| 集合 | 筆數 | 每類 | SQLi骨架群 | XSS骨架群 |
|---|---:|---:|---:|---:|
| train |450|150|7|12|
| test |150|50|2|4|
| Sylius validation |150|50|20|23|
| challenge |96|32|4|8|

主實驗仍60/20/20，challenge另計；Bagisto／Shopware用於train/test/challenge，Sylius只validation，Medusa排除。62API、620文件位置、四種輸入位置及三類配對均保留。API文件內容與舊small-api-v3資料不變。

**請求與模型輸入沒有正規化**：以上解碼／常數處理只產生分組metadata。模型仍用原文（僅遮蔽憑證及必要傳輸序列化）。特徵v5=2402維、150棵／深度3／學習率0.05／seed42不變，只fit train。不加入骨架ID、標籤、平台或集合資訊作特徵。

每個集合的所有來源／配對／骨架關聯合併後仍只有1個相依群，少於20，維持不報信賴區間。test只有2個SQLi骨架、4個XSS骨架，50筆／類不等於50個獨立結構；即使分數高也不能宣稱未知攻擊泛化。新challenge是保留語境群，不再宣稱其家族或所有編碼從未見過。

全部846筆仍offline／exploratory、HTTP=0，歷史ID／條件商品等限制不變，不宣稱正常購物流程、儲存型／DOM行為或注入執行成功。v3已看過的成績影響了方法改進，本次屬方法修正後的探索性比較；論文最終效果需另保留新來源資料。

## 產物與重現

- 新資料：sentinel/dataset/small-api-v4/{train,test,validation,challenge}.csv。
- 骨架目錄：skeleton-catalog.csv；文件覆蓋：field-coverage.csv；規則／來源SHA：provenance.json。
- Colab：sentinel/model/msdss訓練.ipynb、sentinel/model/dataset.zip。兩個都需換新版，第一格拒絕舊協議。
- v3基準：sentinel/dataset/small-api-v3，以及 sentinel/model/history/xss-v3-baseline/ 的原程式／Notebook／ZIP。
- 執行驗證結果：sentinel/dataset/small-api-v4/verification.json。測試用模型在系統暫存目錄，不提交正式模型。

```sh
python sentinel/dataset/build_skeleton_v4.py --output NEW_DATA_DIRECTORY
python sentinel/model/train.py --mode offline --data-dir sentinel/dataset/small-api-v4 --check-only
python sentinel/model/train.py --mode offline --data-dir sentinel/dataset/small-api-v4 --output NEW_RUN_DIRECTORY
python sentinel/model/prepare_colab.py --data-dir sentinel/dataset/small-api-v4 --output NEW_DATASET.zip
```

建立器拒絕覆寫既有資料；先到新目錄重建、核對後再替換衍生產物。Windows驗證不能代替Colab／Ubuntu當地自測。

## 固定參數本機試跑（探索性）

| 集合 | Accuracy | Macro-F1 | SQLi Recall | XSS Recall |
|---|---:|---:|---:|---:|
| test |0.7000|0.7006|0.5000|0.6000|
| Sylius validation |0.6400|0.6299|0.4200|0.6600|
| challenge |0.4688|0.3728|0.0000|0.9062|

同樣固定150棵，沒有依這些分數再修改資料或模型。v3的test97.33%沒有延續到此切分，但考題分布已變，不能用兩個數字宣稱單一因素的因果效果。challenge正常誤報率50%、SQLi召回0，顯示模型仍有明顯缺口；XSS較高召回也不能抵銷這些問題。

完整本機診斷指標、逐筆預測與混淆矩陣保留 small-api-v4/evaluation-smoke/；這些是Windows固定依賴的離線試跑，不是Colab／Linux／真實平台效果。

## Python版本相容性修正

使用者Colab回報「骨架目錄無法由原文重算」。本機以Python3.13.13重現：外部一筆含未封閉HTML註解／CDATA的XSS片段，在3.11被標為HTML骨架，3.13標準庫則成為JS_FRAGMENT。這使簽章與群ID改變；不是HTTP旗標或文件not_available造成，也不是需要刪除的檢查。

修正為專用凍結解析器（CPython3.11.3 HTMLParser與_markupbase，保留PSF授權），再核對解析器ID及檔案SHA。未關閉跨集合骨架檢查，也未將預存簽章當成重算結果。新產生器也使用同一解析器。骨架規則仍v1，CSV、全部846筆原文、ID與分割完全不變；只更新程式、來源指紋與套件。

Python3.11.3／3.13.13各自重算107列目錄與846筆樣本，結果指紋相同，跨集合故意放入同骨架的反例均被拒絕。結果見small-api-v4/parser-compatibility.json。未直接操作Colab或Linux環境；用戶須重新上傳dataset.zip，從第一格重新解壓再檢查。

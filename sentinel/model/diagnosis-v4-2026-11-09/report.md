# v4逐筆誤判與特徵敏感度診斷

固定150棵／深度3／學習率0.05，僅fit train；先逐筆核對既有預測（機率誤差≤1e-6）才分析。沒有重新切分、調參、送HTTP或改寫原始資料。

評估共396筆，誤判150筆；本次三類重點：{"SQLi漏判為正常": 47, "SQLi混淆為XSS": 39, "正常誤報為XSS": 24}。

## SQLi註解特徵的資料偏差

| 集合 | 命中註解特徵 | 筆數 | 判normal | 判sqli | 判xss |
|---|---|---:|---:|---:|---:|
| train | False | 0 | 0 | 0 | 0 |
| train | True | 150 | 0 | 150 | 0 |
| test | False | 25 | 24 | 0 | 1 |
| test | True | 25 | 0 | 25 | 0 |
| validation | False | 29 | 9 | 0 | 20 |
| validation | True | 21 | 0 | 21 | 0 |
| challenge | False | 32 | 14 | 0 | 18 |
| challenge | True | 0 | 0 | 0 | 0 |

註解特徵是現行正則 `--|/\*|\*/`，不包含MySQL的`#`。命中只是字串訊號，不是SQL執行證據。訓練SQLi全部含此訊號，缺少不帶註解的結構，也缺少帶相同符號的正常自由文字對照。

## 僅在副本上的敏感度測試

| 集合 | 操作 | 筆數 | 改變預測 | 原本分布 | 修改後分布 |
|---|---|---:|---:|---|---|
| challenge | append_double_dash | 32 | 32 | {'normal': 14, 'xss': 18} | {'sqli': 32} |
| challenge | neutral_ascii_same_char_length | 15 | 0 | {'xss': 15} | {'xss': 15} |
| challenge | neutral_cjk_same_char_length | 15 | 0 | {'xss': 15} | {'xss': 15} |
| challenge | path_length_feature_only | 32 | 16 | {'normal': 16, 'xss': 16} | {'normal': 32} |
| test | append_double_dash | 25 | 25 | {'normal': 24, 'xss': 1} | {'sqli': 25} |
| test | neutral_ascii_same_char_length | 7 | 0 | {'normal': 7} | {'normal': 7} |
| test | neutral_cjk_same_char_length | 7 | 0 | {'normal': 7} | {'normal': 7} |
| test | path_length_feature_only | 50 | 0 | {'normal': 50} | {'normal': 50} |
| test | remove_double_dash_suffix | 25 | 12 | {'sqli': 25} | {'sqli': 13, 'xss': 12} |
| train | neutral_ascii_same_char_length | 76 | 0 | {'normal': 76} | {'normal': 76} |
| train | neutral_cjk_same_char_length | 76 | 0 | {'normal': 76} | {'normal': 76} |
| train | remove_double_dash_suffix | 150 | 150 | {'sqli': 150} | {'normal': 77, 'xss': 73} |
| validation | append_double_dash | 29 | 28 | {'xss': 20, 'normal': 9} | {'sqli': 28, 'xss': 1} |
| validation | neutral_ascii_same_char_length | 1 | 0 | {'normal': 1} | {'normal': 1} |
| validation | neutral_cjk_same_char_length | 1 | 0 | {'normal': 1} | {'normal': 1} |
| validation | path_length_feature_only | 50 | 8 | {'normal': 42, 'xss': 8} | {'normal': 50} |
| validation | remove_double_dash_suffix | 21 | 21 | {'sqli': 21} | {'xss': 11, 'normal': 10} |

以上是特徵敏感度探針，替換後的值不是新增訓練資料或實機有效SQL；文字長度控制為Python字元數，沒有控制UTF-8位元組長度、語意或每個ngram，不能據此斷言中文本身造成誤報。未對照部署效果或校準門檻。

## API文件與標籤限制

samples.csv及focus-errors.csv逐筆連結文件欄位、行號、含義、型別與可輸入值；不改三份API文件。攻擊只表示payload來源意圖，在語言／貨幣／數字欄可能不合型別或enum。正常候選也未實機驗證，不能把它們的誤報率當作真實商店使用者誤報率。

SQL結構片段CASE／COLLATE只有在可執行SQL語境才有注入意義；作搜尋文字也可為字面內容。僅憑請求無法證明惡意成功，保留原標籤與脈絡限制，不為提高分數重新標記。

## 特徵能否看到差異

攻擊與其正常配對2402維完全相同的樣本：0筆。可見差異不代表樹有學到有效決策。feature-gain.csv是模型分裂增益，不是因果解釋；hash桶有碰撞，不把桶名解釋成唯一關鍵字。

## 後續補強的界線

目前test／validation／challenge已被檢視，只作診斷，不反覆改到高分。保留這些資料與參數；若新增train，先與完整骨架目錄比對，碰到任何保留骨架就排除，不能把本輪錯題複製到train。

優先新增獨立來源的不帶註解SQL結構、不同SQL方言與字面程式碼／符號正常對照。依既有API文件只將正常文字放合適自由文字欄，保持三類相同位置分布與近似長度；分開記錄不合型別的攻擊候選。需另建立新且未檢視的跨來源評估集，不能沿用本輪資料宣稱最終泛化。

本輪診斷不新增訓練資料、不改模型或打包檔，避免把診斷當成模型改進已驗證。完整逐筆證據見同目錄CSV與audit.json。

## TreeSHAP分數分解與路徑長度探針

error-shap.csv保存重點誤判的前8項貢獻。分解的是預測類別減真實類別的原始margin差，非機率或因果效果；已核對加總守恆。hash桶可能碰撞。

| 集合 | 誤判類型 | 筆數 | 平均正向貢獻最高群 |
|---|---|---:|---|
| challenge | SQLi混淆為XSS | 18 | query.sql_comment: 0.673；headers.aggregate.sql_comment: 0.628；body.sql_comment: 0.604；path.sql_comment: 0.513 |
| challenge | SQLi漏判為正常 | 14 | query.sql_comment: 0.672；headers.aggregate.sql_comment: 0.629；body.sql_comment: 0.605；path.sql_comment: 0.513 |
| challenge | 正常誤報為XSS | 16 | path.length: 2.964；path.hash_buckets: 0.647；body.symbol.'{': 0.020；body.symbol.'$': 0.016 |
| test | SQLi混淆為XSS | 1 | query.hash_buckets: 0.750；query.sql_comment: 0.672；headers.aggregate.sql_comment: 0.627；body.sql_comment: 0.603 |
| test | SQLi漏判為正常 | 24 | query.sql_comment: 0.672；headers.aggregate.sql_comment: 0.628；body.sql_comment: 0.604；path.sql_comment: 0.513 |
| validation | SQLi混淆為XSS | 20 | query.sql_comment: 0.674；headers.aggregate.sql_comment: 0.628；body.sql_comment: 0.604；query.extra_regex.5: 0.592 |
| validation | SQLi漏判為正常 | 9 | query.sql_comment: 0.672；headers.aggregate.sql_comment: 0.628；body.sql_comment: 0.604；path.sql_comment: 0.513 |
| validation | 正常誤報為XSS | 8 | path.length: 2.938；body.hash_buckets: 0.069；body.symbol.'/': 0.015；body.xss_event: 0.006 |

path_length_feature_only只把特徵向量第40格設為train正常樣本中位數，原始path與所有其他特徵不動。這是數值敏感度探針，向量可能不對應任何真實HTTP請求，不能當作資料正規化、修正後模型或新評估成績。

# v4誤判診斷：SQL註解捷徑與路徑長度偏差

日期：2026-11-09。此輪只讀既有v4資料與評估結果，產生診斷程式與獨立紀錄，不修改三份API文件、資料集、訓練／推論入口、Colab套件或平台服務。不發送HTTP、不執行SQL／JS。

## 核對範圍

同一固定模型參數（150棵、深度3、學習率0.05、seed42），只fit450筆train。重現396筆評估預測，與現存predictions.csv所有類別與機率完全一致（最大誤差0）。以下依這個模型分析，不據此重新選參數。

396筆評估中共150筆分類錯誤。本輪完整逐筆檢查三個重點，共110筆：SQLi→normal47筆、SQLi→XSS39筆、normal→XSS24筆。其餘40筆錯誤（XSS→normal／SQLi）也保存在all-evaluation-errors.csv，不假裝所有問題已解決。

## 發現一：SQLi過度依靠註解符號

訓練150筆SQLi全部命中目前的 `--|/\*|\*/` 特徵。評估集命中的46筆SQLi全部判對；沒命中的86筆SQLi全部判錯。

| 集合 | 無註解特徵的SQLi | 判normal | 判XSS |
|---|---:|---:|---:|
| test |25|24|1|
| Sylius validation |29|9|20|
| challenge |32|14|18|

test的25筆無此特徵者全部使用原文 `1 OR 1=1`，不是25個獨立骨架。challenge四個SQL結構片段每個使用8次：CASE WHEN、子查詢排序片段、COLLATE、CASE子查詢。模型沒有正確辨識這四群。

在副本追加 ` -- `，86筆原錯題有85筆改判SQLi（test25/25、validation28/29、challenge32/32）；train去掉原文尾端 `--` 後，150/150從SQLi轉成normal或XSS。分裂增益最高四格也都是各通道的sql_comment。

這是很強的模型敏感度證據，顯示目前生成分布讓註解符號成為分類捷徑。不是建議給資料補 `--` 提高分數。`#`也是部分SQL方言的註解形式，現行正則未涵蓋；但僅補一個符號仍無法解決結構涵蓋不足。副本修改不等於有效SQL或注入成功。

## 發現二：正常誤報集中在路徑長度

challenge的16筆normal→XSS全來自Shopware `/product-listing/{categoryId}`。其中15筆有額外正常說明文字，1筆沒有。將說明文字換成同字數英文 `N` 或中文字，15筆仍全部判XSS，所以不能把相關性解讀成「中文造成誤報」。train的搜尋API正常本文也有922–954字元，比challenge商品列表896–902字元更長，不能單靠「JSON本文太長」解釋。

TreeSHAP將預測XSS減真實normal的原始分數差分解；24筆normal誤報的最大平均正向群都是 `path.length`：challenge約2.964、Sylius validation約2.938。這是原始分數貢獻，不是機率或因果證明。

再做單維數值探針：只將向量第40格path.length設為train正常路徑長度中位數17，其餘特徵與原始path完全不動。

| 集合 | 原本normal→XSS | 探針後normal→XSS |
|---|---:|---:|
| test |0|0|
| Sylius validation |8|0|
| challenge |16|0|

全部24筆改判normal，支持此模型對路徑長度高度依賴。這個向量不一定對應任何真實請求，**不是修改後模型的評估分數，也不是建議把ID／路徑正規化**。原始輸入仍按使用者要求保留。後續若考慮特徵選擇，需在train內獨立分組開發驗證，不能以本輪保留集挑出最高分版本。

## API文件核對與標籤限制

三份API文件雜湊、各目標欄位型別／含義／可輸入值／來源行號已記在audit.json與samples.csv。完整正常基準沒有單一替換目標者，以平台與API回查原文件；不能虛構一個「造成誤報」的參數。

攻擊候選仍會注入文件限制為整數、固定語言或貨幣的欄位，可能被平台型別／enum檢查拒絕；正常請求也仍是未實機驗證的候選。CASE／COLLATE等片段只有在可執行SQL語境才有注入意義，出現在搜尋或教材文字也可能只是字面內容。本輪不為分數改標籤，不宣稱平台漏洞或正常業務流程成功。

所有攻擊與正常配對的2402維向量都有差異（完全相同0筆），因此不是整批payload被輸入流程吃掉；能看到差異仍不代表模型學到可靠規則。hash桶可能碰撞，不把桶的貢獻解釋為唯一關鍵字。

## 接下來應補強的項目

| 問題 | 補強方向 | 避免破壞評估的條件 |
|---|---|---|
| SQLi全部帶註解 | 增加獨立來源、不帶註解的SQL結構與方言，並加入含相同符號的正常自由文字對照 | 新增train先與完整保留骨架目錄比對；不複製本輪錯題或其近似骨架 |
| 路徑長度成為XSS線索 | 檢查train內標籤與長度分布，增加文件允許且有真實來源的正常長路徑／短攻擊案例 | 不亂加路徑段或偽造ID；文件不允許就標記資料限制，特徵選擇只在train內驗證 |
| 複雜購物請求正常誤報 | 依三份文件補正常購物情境、巢狀本文與字面程式碼控制，維持位置分布 | 只在允許自由文字的欄位加入教材／符號文字，不把無效enum當正常 |
| 少數骨架重複嵌入多個API | 優先增加不同結構、來源與真實流程，而不是同一句換14個尾數 | 保留骨架／配對／來源關聯，新的最終評估來源另行凍結 |

這些是後續資料與研究設計要求，本輪尚未新增資料或驗證改進後模型。三份保留集已被檢視，只作診斷，不能反覆調到漂亮後當最終未見評估；各集合仍一個合併相依群，不能報獨立信賴區間。

## 產物與重現

- `sentinel/model/diagnose_v4_errors.py`：可重跑的診斷工具，拒絕覆寫舊輸出。
- `sentinel/model/diagnosis-v4-2026-11-09/report.md`、`audit.json`：完整方法、分組與探針摘要。
- `focus-errors.csv`：110筆重點錯誤，含API、欄位、payload、預測機率與文件定義。
- `all-evaluation-errors.csv`：全部150筆誤判。
- `counterfactuals.csv`：副本／單維向量探針逐筆結果，不是新資料集。
- `error-shap.csv`、`feature-gain.csv`：分數分解與分裂增益。
- `samples.csv`、`group-breakdown.csv`：846筆逐筆與按家族／位置彙整。

```sh
python -m pip install -r sentinel/model/requirements.txt
python sentinel/model/diagnose_v4_errors.py --data-dir sentinel/dataset/small-api-v4 --results-dir sentinel/dataset/small-api-v4/evaluation-smoke --output NEW_DIAGNOSIS_DIRECTORY
```

在Windows固定依賴NumPy2.3.5／scikit-learn1.7.2／XGBoost3.1.2執行。未直接讀取使用者Colab磁碟中的predictions.csv；本次使用專案保留的本機結果，其矩陣／數值與使用者貼出的Colab結果一致。若需核對另一份Colab逐筆結果，傳入其results-dir，機率差異超過1e-6會停止分析。

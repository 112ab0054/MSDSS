# 2026-11-09：只補強訓練資料 v5

使用者同意依v4誤判診斷補強資料。本次只新增train，保留v4資料與三份保留CSV、API文件、特徵v5、原始輸入方式與模型參數。沒有改Medusa／Mirage／根目錄compose或資料庫，沒有發送HTTP。

## 實作與筆數

| 集合 | 每類 | 合計 | 變化 |
|---|---:|---:|---|
| train（Bagisto／Shopware）|198|594|新增144筆|
| test（Bagisto／Shopware）|50|150|原檔凍結|
| validation（Sylius＋httpParamsDataset）|50|150|原檔凍結|
| challenge（Bagisto／Shopware）|32|96|原檔凍結|
| 總計 |330|990|由846增加144|

原450筆train完整保留；新增48組normal／SQLi／XSS控制配對，每類各48筆，四位置header／body／query／path各12筆。新增Bagisto54／Shopware90；最終train Bagisto195／Shopware399。主比例變為594:150:150，不能再標60/20/20；因為只補train，沒有為維持比例把已看過的題重新洗牌。

新增24種無註解SQL片段（條件、EXISTS／IN、子查詢、集合比較、函式、轉型、字串結合等），每種嵌入2筆；新增24種短／長JS與HTML片段（23群骨架），也各嵌入2筆。片段為本次本地策劃，沒有冒稱新增獨立外部來源。正常對照包含文件搜尋／備註等自由文字中的註解符號／程式碼教材，以及公司名稱中的合法標點；companyName只用公司名稱，未放教材或攻擊字串。

依三份API文件逐筆選用已宣告欄位，新增96筆攻擊的欄位含義／型別／文件行號與正常控制所在欄位記在augmentation-bindings.csv，未改原文件。620欄位位置仍全覆蓋。攻擊可能違反型別／enum，正常公司及歷史ID仍屬未實測候選；未宣稱平台接受或業務成功。

## 隔離與重現

候選在模型評估前固定。每個新候選先對全v4骨架目錄分組，再額外作跨家族原文相似度≥0.90檢查；若碰到任何舊骨架或近似字串就排除，保守連舊train重疊也不新增。此次48個候選全通過；保留candidate-decisions.csv，不按模型分數挑選。

合併新目錄後再次確保原107列骨架簽章與ID完全不變，沒有藉新案例串連原群。骨架規則／protocol仍document-v4-skeleton-disjoint，資料revision另標v5-train-augmentation。train骨架由SQLi7／XSS12增加至SQLi31／XSS35。正常／攻擊控制與來源模板分組仍保留，每個集合合併相依群仍只有1，不能報獨立信賴區間。

preflight新增v5保留集SHA核對。test／validation／challenge的CSV整檔bytes與v4完全相同。Python3.11.3／3.13.13都重算990筆骨架檢查通過；兩個PYTHONHASHSEED17／153重建全部產物一致。凍結解析器及PSF授權隨Colab包保留。

## 一次固定參數比較

只fit train，維持150棵、深度3、學習率0.05、seed42、CPU/hist、2402維特徵。新資料凍結後只作一次比較，沒有依新分數再改案例／調參。

| 集合 | v4 Accuracy | v5 Accuracy | v4 Macro-F1 | v5 Macro-F1 |
|---|---:|---:|---:|---:|
| test |0.7000|0.8400|0.7006|0.8399|
| Sylius validation |0.6400|0.8400|0.6299|0.8365|
| challenge |0.4688|0.7396|0.3728|0.6861|

| v5集合 | SQLi Recall | XSS Recall | 正常誤報率 |
|---|---:|---:|---:|
| test |0.7400|0.8000|0.0200|
| Sylius validation |0.7600|0.7600|0.0000|
| challenge |0.2500|0.9688|0.0000|

正常誤報有改善，但challenge仍有24/32的SQLi未正確分類。新增資料數量、骨架與正常對照同時改變，不能用此比較斷言某單一因素的因果效果。正常長路徑的真實涵蓋缺口仍未補齊，沒有編造API路徑、改UUID長度或捏造真實ID來填數。

目前三份保留資料已被觀察，資料策劃也受到v4錯誤類型啟發，因此是探索性比較；不能宣稱最終未見來源／家族泛化。需要另留新來源與新流程作最終評估，不能反覆改到漂亮後宣稱有效。全部資料仍offline／exploratory、HTTP=0。

## 產物與執行

- 資料：sentinel/dataset/small-api-v5，內含四集合CSV、來源指紋、骨架目錄、文件覆蓋、候選決策與綁定明細。
- 結果：small-api-v5/evaluation-smoke，含逐筆預測、完整報告與混淆矩陣。
- 驗證：small-api-v5/verification.json及parser-compatibility.json。
- Colab：沿用sentinel/model/msdss訓練.ipynb與dataset.zip，重新上傳並從第一格執行；首格核對v5 revision。
- 舊版：small-api-v4及model/history/train-v4-baseline，保留原450筆基準與可用Python3.13的舊ZIP／Notebook。

```sh
python sentinel/dataset/build_train_v5.py --output NEW_DATA_DIRECTORY
python sentinel/model/train.py --mode offline --data-dir sentinel/dataset/small-api-v5 --check-only
python sentinel/model/train.py --mode offline --data-dir sentinel/dataset/small-api-v5 --output NEW_RESULT_DIRECTORY
python sentinel/model/prepare_colab.py --data-dir sentinel/dataset/small-api-v5 --output NEW_DATASET.zip
```

本次實際完成Windows固定依賴的打包、解壓、訓練與搬移推論self-test。Python3.13完成骨架重算，不冒充已在Colab／Ubuntu服務直接實測。沒有提交暫存測試模型為正式部署模型。

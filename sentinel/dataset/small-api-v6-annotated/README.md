# v6攻擊面向閱讀版

本版只在四份CSV的「類別」旁新增一欄「攻擊面向」，多面向用全形分號分隔。normal顯示不適用；可見結構不足者標成待確認或未細分。不是已驗證的攻擊效果，也不假造反射型／儲存型／DOM型標註。
原small-api-v6完整保留，1098筆、sample ID、三類標籤、原始請求、完整紀錄JSON與骨架／集合不變。因為加了顯示欄，CSV整檔SHA必然改變；本目錄的凍結SHA明確對應閱讀版，原始SHA另外保存，不能把新SHA假稱為舊CSV完全一樣。
訓練讀取完整紀錄JSON，不讀這個顯示欄，模型／推論特徵與結果不因此改變，不需重新訓練。新Colab套件會帶這些CSV。
規則、計數與限制見attack-facets-rules.json；原始欄位與完整紀錄逐筆讀回核對一致，來源追溯見provenance.json的display_annotation。
本輪不處理前次分析指出的111筆normal的sw-language-id格式問題，也不更改外部來源XSS標籤；這些問題仍保留待後續處理。

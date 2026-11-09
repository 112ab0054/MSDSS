# 專案目前狀態

更新：2026-11-10。實際工作副本為C:/Users/USER/Documents/GitHub/MSDSS。Downloads/MSDSS是先前來源，不在那裡繼續修改。

## 資料與模型

- 目標三類normal、sqli、xss。Bagisto與Shopware供train／test；Sylius結合httpParamsDataset payload作獨立validation；Medusa只作教授展示，不入資料集。
- 本機只保留sentinel/dataset/small-api-v9，共1098筆：train702、test150、validation150、challenge96。舊v1～v8及中間輸出已刪，需要追溯由Git歷史還原。
- 全部仍是offline候選，不冒稱HTTP全實測。保留原始輸入，不做正規化；骨架只供分組，不取代特徵輸入。各split的相依群組仍少，不能據此宣稱穩定泛化。
- 三份參數文件在analysis/selected-api-contracts/，不可任意改參數含意與範例。v9內保留語義規則、來源與資料庫快照；自由文字多樣化、地址關聯一致，憑證遮蔽。
- model/train.py／training.py是訓練入口，msdss訓練.ipynb與dataset.zip供Colab；ZIP已按當前程式重打包，四份CSV與v9完全一致，解壓後離線檢查通過。
- 現用完整模型是sentinel/gateway/model/，使用者Colab v9輸出；feature v6、input v3、2402維，offline／exploratory。model SHA為e612214de592b01ec931cc73a100603928c89e747c61eebf3027424669f24993。清理未改模型、特徵或請求資料。
- 最新評估在model/results/colab-v9-2026-11-09。歷程見[白話紀錄](訓練版本與問題處理白話紀錄.md)，文內舊檔案位置是歷史，不代表本機仍保留。

## Medusa 與gateway

- API參考清單精確還原原始77項，使用者確認保留reset-password。根Medusa_77_API_填寫參數.md是原快照逐bytes還原。原新增POST /store/search與付款session更新兩項已移出參考清單，歷史證據保留。
- 真實本機Medusa是2.21.0，入口9100；bundled規格2.22.3、專案2.22.4不能當成當前執行版本。77項目前60成功、1部分成功、7前置不足、9功能／版本差異，not_run=0。
- gateway分析所有經過它、支援的HTTP方法／路徑，不以77清單篩選。忙碌排隊，GATEWAY_ANALYSIS_TIMEOUT現在是等待告警門檻，不取消推論。觀察模式不因模型判斷封鎖；未載入／推論錯誤仍如實記錄並轉送。
- 已更新本專題自己的18085 HTTP、18443 HTTPS入口，均只綁127.0.0.1並轉9100。其他Medusa／Mirage／storefront服務與根compose未改。沒有遠端部署或更改隊友repo。
- 真實補驗6筆gateway請求及6筆直連狀態相符，gateway6筆均有UUID對應分數。這是接線，非準確率。模型工具41項測試及gateway19項、runtime12項已通過；本輪刪舊版後測試改用v9，沒有改成skip來避開失敗。
- 密碼重設HTTP確實生成新Token、使舊Token失效，但沒有事件消費／郵件送達證據，仍部分成功。MFA缺加密設定、OAuth未配第三方、manual不支援動態運費、translation停用，其餘缺路由，不假裝新增資料能解決。

## 清理與交付

本機已移除舊資料v1～v8、舊模型zip、舊模型history、舊診斷與專用比較測試。保留當前資料／模型／訓練程式、共用骨架解析器與授權、原始API來源、HTTP證據及必要快照。.runtime含私有設定與憑證，不加入Git；不要整包刪除。帶版本號的build程式有共用函式仍被目前測試使用，不能只按名稱刪。

目前包含先前77項／全路徑gateway調整和本機清理的未提交變更。不要自動push到舊repo冒充隊友repo；隊友目標尚未提供。不要刪除其他資料、重置資料庫或停止不屬於本次專題的服務。

啟動與行為見[gateway README](../gateway/README.md)，訓練見[model README](../model/README.md)，Medusa證據見[77項與全路徑說明](Medusa驗證與展示.md)。

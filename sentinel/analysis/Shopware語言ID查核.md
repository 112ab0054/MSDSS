# Shopware 的 sw-language-id 應該填什麼

查核日期：2026-11-09。對象是獨立本機 Shopware 6.7.15.1，位址 http://127.0.0.1:18082。

## 目前能確定的值

| 語言 | locale | sw-language-id | 證據與限制 |
| --- | --- | --- | --- |
| English | en-GB | `2fbb5fe2e29a4d70aa5854ce7ce3e20b` | 歷史 passed 實機報告的 context.languageIdChain、salesChannel.languageId 與 languageInfo 對應一致；本次尚未重新連線確認 |

證據：`../local-platforms/reports/shopware-057a8b6d60664a2d9651c52498dc172d.json`。其他歷史成功報告也出現同一個 ID。

「目前只證實一個」不等於「系統只建立一種語言」。原本說這個設定值應該一致，語氣太肯定；正確說法是：尚未取得其他已驗證的可用 ID，暫時只能使用已知值，不能宣稱沒有其他值。

## 正確填法

這個 header 選擇商店的內容語言，填資料庫的語言 ID，不是直接填 `en-GB`、`de-DE` 或 `zh-TW`。ID 是 32 個十六進位字元，但格式正確不代表商店真的有這個語言，也不代表目前銷售通路允許使用。

Shopware 可以建立多種語言，再把需要的語言加入銷售通路。若本機已開放英文與德文，正常資料就可以使用各自的真實 ID；若實際只開放英文，重複使用英文 ID 是合法設定，不能為了多樣性捏造其他 ID。

## 本次實際檢查

- 查官方語言與銷售通路說明，並核對固定版本 v6.7.15.1 的 LanguageRoute，確認支援 GET /store-api/language。
- 歷史公開 JSON 未找到額外的完整 language 實體清單；已知英文 ID 不能拿來推定其他語言的 ID。
- C 槽約剩 5.23 GiB，啟動前可用記憶體約 3.89 GiB，後續量測約 3.27 GiB。
- 已嘗試啟動 Docker Desktop，但 Docker 引擎查詢逾時；Shopware 18082 無法連線。
- 已執行新查詢工具，結果 verified=false，尚未取得當前語言清單。這不是「清單為空」，而是「查詢沒有成功」。
- 沒有修改語言設定、資料庫、原 API 文件、資料集或模型，也沒有停止其他服務。

## 可重跑的查詢

在專案根目錄執行：

```powershell
python -X utf8 -B sentinel/local-platforms/inspect_shopware_languages.py
```

先確保既有獨立 Shopware 已啟動。工具從 .runtime/shopware.json 私下讀取存取金鑰，分頁 GET /store-api/language，然後逐個 ID 呼叫 GET /store-api/context。只有實際語言鏈第一個 ID 與送入值相同才記 accepted=true；不只看 HTTP 200。輸出只保留語言資訊，不保存金鑰、登入憑證或 context token。

結果在 `../local-platforms/reports/shopware-language-inventory.json`。此 Store API 清單用於目前銷售通路；不能把它當成整套資料庫所有語言的管理清單。若要查整套系統已建立但未分配通路的語言，還需另外查管理端或唯讀資料庫。

後續只有查到且通過 context 驗證的其他 ID，才能擴充正常資料的語言值。新增語言或分配銷售通路是設定變更，和「查已有什麼值」是兩件事。

## 官方依據

- [語言管理](https://docs.shopware.com/en/shopware-6-en/settings/languages)
- [銷售通路設定](https://docs.shopware.com/en/shopware-6-en/settings/saleschannel)
- [v6.7.15.1 LanguageRoute 原始碼](https://github.com/shopware/shopware/blob/v6.7.15.1/src/Core/System/Language/SalesChannel/LanguageRoute.php)


## 後續已完成：當前實機查詢及 v8 修改

先前失敗紀錄保留作為歷程；本節取代「尚未查到第二個值」的當前狀態。

Docker啟動失敗來自Windows無法存取的AF_UNIX通訊檔。單檔改名失敗，將故障Docker runtime資料夾改名完整保留後恢復；未Factory Reset、prune、清除資料、變更Medusa／Mirage設定。其他服務由Docker自身啟動規則恢復，本次沒有另行停止它們。問題類型可參考[Docker官方專案issue](https://github.com/docker/desktop-feedback/issues/460)，是否適用本機以實際錯誤log為準。

獨立Shopware啟動檢查通過：C槽5.15GiB、Windows空閒1.06GiB、WSL可用6.2GiB，可回收快取計入後餘裕2.8GiB。只啟動本次的Shopware，沒有另啟動Bagisto／Sylius。

實機查核時間：2026-11-09T10:15:14.260164+00:00。

| 語言 | locale | 實際ID | context回應 |
| --- | --- | --- | --- |
| 德文 | de-DE | `01a162e6e938738db9be38797c416637` | 語言鏈首個ID與輸入一致、locale=de-DE |
| 英文 | en-GB | `2fbb5fe2e29a4d70aa5854ce7ce3e20b` | 語言鏈首個ID與輸入一致、locale=en-GB |

兩個都是目前通路可用的值。只送GET語言與context查詢，沒有新增語言或修改銷售通路設定。證據見 `../dataset/small-api-v8/shopware-language-inventory.json`（已凍結副本，沒有金鑰及token）。

111筆normal語言欄位分配：

| 集合 | 德文 | 英文 |
| --- | ---: | ---: |
| train | 42 | 41 |
| test | 7 | 6 |
| validation（Sylius） | 0 | 0 |
| challenge | 8 | 7 |
| 合計 | 57 | 54 |

依normal配對輪流分配，不依模型分數選值；同組SQLi／XSS背景header同步修改。如果攻擊本來就是放在sw-language-id，該筆仍保留攻擊文字，不改成合法ID。總共145筆實際請求輸入改變。v8保留原1098筆、標籤、split、骨架與payload，Sylius驗證集CSV未改。這仍是離線分類資料，只有語言查詢實機驗證，不能標成1098筆全部HTTP已執行。

原v7資料與Colab套件保留。新Colab套件用v8，需要重新訓練；本次沒有替換gateway模型、inference-v7.zip或宣稱模型分數改善。


v8完成核對：57項模型工具測試通過；新版ZIP清單指紋全部吻合，解壓到獨立含空白路徑後，訓練前檢查ready=true、共1098筆；Notebook程式碼語法通過。查詢後已停止本次獨立Shopware以釋放資源，未停止其他服務。尚未重訓或push。


## 再查完整資料庫與其他平台語言欄位

2026-11-09再次啟動獨立Shopware，使用PDO唯讀交易查language LEFT JOIN locale，並檢查sales_channel_language。實際language資料列只有英文en-GB與德文de-DE，兩者都分配目前銷售通路。locale表有252個語系定義，這是可供建立語言時選用的語系目錄，不是252個已啟用語言。公開結果在 `../local-platforms/reports/shopware-language-database-inventory.json`。沒有新增語言或更改通路設定。

唯讀查詢使用SET TRANSACTION READ ONLY，查id、name、locale code、parent_id、是否分配目前通路後rollback；沒有輸出DATABASE_URL、密碼或access key。

重新掃描v8的normal輸入（不是掃標籤或回應）：

| 平台與欄位 | 目前值與筆數 | 可否變動 |
| --- | --- | --- |
| Shopware header sw-language-id | 德文57、英文54 | 已以實機確認的兩個ID變動 |
| Shopware body languageId | 英文ID 1筆 | 同樣使用實際語言ID，可按該操作語意改為德文ID，不能直接填de-DE；v8尚未改此筆 |
| Bagisto header X-Locale | en 88筆 | 文件範例不是固定值；需要以該平台與通路實際啟用語系驗證後擴充 |
| Sylius header Accept-Language | en_US 33筆 | 文件列en_US、de_DE、fr_FR、pl_PL、es_ES、es_MX、pt_PT、zh_CN、fr_GQ；仍要核對目前通路可用性，v8尚未擴充 |

三份選定API文件未直接出現en-GB字面值；它是在Shopware實際語系資訊中出現。不同平台的語言格式不可一律互換，例如Shopware用32位ID、Bagisto文件例子en、Sylius文件列en_US。

本次是補查與說明，尚未建立新資料版本或修改v8 CSV／ZIP；不能把此段紀錄當成其他兩平台語系已完成實測。

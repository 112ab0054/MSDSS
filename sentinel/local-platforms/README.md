# 第一階段：三平台本機正常流程

此目錄獨立於根目錄 Medusa 與隊友 Mirage。僅處理本機真實平台的正常購物驗證，不是訓練資料收集器；沒有產生 SQLi／XSS 資料或訓練模型。執行狀態以 `reports/` 的實測證據為準，程式存在或設定檢查通過不代表流程成功。

## 固定版本與隔離

| 平台 | 固定來源 | 本機入口 | 獨立 Compose project |
|---|---|---|---|
| Bagisto | 核心 2.4.10／API 2.4.4 | http://127.0.0.1:18081 | msdss-phase1-bagisto |
| Shopware | 6.7.15.1，Dockware 映像同時固定 digest | http://127.0.0.1:18082 | msdss-phase1-shopware |
| Sylius | Standard 範本 2.2.4／核心 2.2.12 | http://127.0.0.1:18083 | msdss-phase1-sylius |

完整 commit、映像 digest 見 [versions.json](versions.json)。Sylius 範本版本與核心套件版本分開固定；未使用已封存的 Docker-Standard。Bagisto／Sylius 共用固定 PHP 8.3.30 建置設定，各有獨立資料庫、網路與資料卷，資料庫不開放主機埠。Shopware 自帶的 PHP／MySQL 屬於其固定映像，實際版本另記錄。

參考：[Bagisto 2.4.10 Composer](https://github.com/bagisto/bagisto/blob/72beea139e644e9e1b6981b717d57dfa68ad3106/composer.json)、[API 2.4.4 說明](https://github.com/bagisto/bagisto-api/tree/968cfe114090fb7c74f4169d9116cde6099def84)、[Shopware 固定版本](https://github.com/shopware/shopware/tree/fc6b754982a0328200ffd3f8d795664a0a6e8447)、[Dockware 啟動說明](https://docs.dockware.io/dockware-shopware/getting-started)、[Sylius Standard 固定來源](https://github.com/Sylius/Sylius-Standard/tree/6b580309567f2cf9b840e98efca2c7e3544a55bd)。

## 啟動與停止

從 `C:/Users/USER/Downloads/MSDSS` 使用 PowerShell 7 執行。只逐個啟動，不使用根目錄 compose。`stop` 保留資料，不會刪除 volume。

```powershell
./sentinel/local-platforms/manage.ps1 -Platform shopware -Action start
./sentinel/local-platforms/manage.ps1 -Platform shopware -Action status
./sentinel/local-platforms/manage.ps1 -Platform shopware -Action stop
```

`-Platform` 可為 `bagisto`、`shopware`、`sylius`。啟動前先執行資源檢查；若另一個本次平台仍在執行便停止啟動動作，不會代替使用者停止其他服務。

資源檢查同時記錄 Windows 可用 RAM、WSL MemAvailable 與可回收檔案快取。單平台上限至多 1.5 GiB，另保留 0.75 GiB 餘裕；Windows 可用低於 0.75 GiB 或 WSL 可用不足 3 GiB 時拒絕啟動。共享映像建置後，後續操作前至少保留 6 GiB 磁碟空間；這不代表首次下載安裝大小保證，安裝過程仍須持續檢查。程式不會自動清理資料。

## 第一次初始化與種子

Shopware 使用固定 Dockware 映像內的初始資料（通路、商品、國家、配送與付款）。第一次解壓與啟動需要時間，先等容器 ready，再執行：

```powershell
./sentinel/local-platforms/shopware/bootstrap.ps1
python sentinel/local-platforms/run_shopware.py
```

Bootstrap 只操作有正確 project 標籤的本次容器：設定本機通路網址、關閉測試通路註冊的雙重郵件確認、讀取 storefront key，並從資料庫核對原生 InvoicePayment／CashPayment handler 的 ID。Store API 不回傳 handler，因此不能僅用 API 的顯示名稱推定付款方式。主流程只從回應的可用方式選取已核對的離線付款 ID，不呼叫外部付款頁或 handle-payment。

Bagisto／Sylius：

```powershell
./sentinel/local-platforms/prepare.ps1 -Platform bagisto
./sentinel/local-platforms/init.ps1 -Platform bagisto
./sentinel/local-platforms/manage.ps1 -Platform bagisto -Action start
python sentinel/local-platforms/run_bagisto.py
./sentinel/local-platforms/manage.ps1 -Platform bagisto -Action stop

./sentinel/local-platforms/prepare.ps1 -Platform sylius
./sentinel/local-platforms/init.ps1 -Platform sylius
./sentinel/local-platforms/manage.ps1 -Platform sylius -Action start
python sentinel/local-platforms/run_sylius.py
./sentinel/local-platforms/manage.ps1 -Platform sylius -Action stop
```

`prepare` 只下載固定 commit、將指定 API／核心相依固定為明確版本，產生本機隨機資料庫憑證；不執行資料庫操作。首次 Composer 解析後保存 lock 到 `locks/`，尚未產出 lock 的平台不能宣稱所有間接相依已可重現。`init` 僅允許 `db` 主機與 `msdss_平台` 資料庫，先核對資料庫沒有任何表，已有表或初始化標記便拒絕重灌。Bagisto 官方安裝器包含 wipe，不能直接對其他資料庫執行。

Bagisto 種子建立 SKU `MSDSS-PHASE1-SIMPLE` 的實體單品、庫存 100、價格 25、預設通路與索引；啟用本機固定費率配送與貨到付款／轉帳、停用測試通路的郵件驗證，產生真實 storefront key，並更換預設管理員密碼。Sylius 使用官方 default fixtures，再核對可用通路／國家與 gateway factory 為 `offline` 的付款方式，將通路主機設為本機，並更換管理員密碼。原始安裝輸出可能含安裝器的預設帳密，因此只放忽略提交的 `.runtime`，分享前必須遮蔽。

若初始化中途失敗，不要直接重跑具破壞性的安裝器。先用下列方式檢查已遮蔽的最後輸出，再依失敗步驟續作；已有表的資料庫會被重灌保護擋住。

```powershell
./sentinel/local-platforms/show-private-log.ps1 -Name bagisto
```

## 請求與驗證證據

三個 runner 僅連 `http://127.0.0.1`，不使用主機 HTTP proxy、不跟隨跳轉。每次建立新的測試會員；商品、購物車、品項、地址、配送、付款與訂單 ID 均取自當次回應。Token／Cookie 僅在記憶體延續，註冊密碼隨機生成。Sylius PATCH 使用 `application/merge-patch+json`。

每次另存 `reports/平台-隨機值.json`，包含 request ID、已遮蔽請求／回應與業務斷言。失敗立即停止，不以 HTTP 200 宣稱成功。`passed` 要完成重新讀取購物車數量、刪除結果、地址、配送付款與新訂單內容／狀態。離線待付款的訂單不等於已實際付款。Bagisto 的訂單明細讀取屬額外支援操作，不混入原本 21 個選定操作。

`.runtime/` 包含真實憑證、來源 checkout、vendor、私有安裝輸出與初始化標記，已由此目錄的 `.gitignore` 排除，不能公開或當成訓練資料。請勿將該目錄打包上傳。公開的 `reports/` 與原有採用清單分開維護；`ready_for_collection` 仍保持 false。

```powershell
python -m unittest discover -s sentinel/local-platforms -p test_evidence_privacy.py
python sentinel/local-platforms/audit.py
python sentinel/scripts/active_api_contracts.py
```

遮蔽測試只測紀錄工具，不測平台，也沒有用虛假 HTTP 回應當成購物流程證據。`audit` 輸出逐 API 的 [JSON](reports/api-status.json)／[CSV](reports/api-status.csv)，只採用完整 `passed` 且有業務斷言的實測證據；未呼叫的操作維持尚未測試。契約比較與保護檔案的 SHA-256 核對不能代替實機驗證。

## 2026-11-08 接續核對紀錄

已依固定實例的最新完整正常流程證據重新核對三個電商 API：

| 平台 | 選定操作 | 最新完整流程報告 | 結果 |
|---|---:|---|---|
| Bagisto 2.4.10／API 2.4.4 | 21 | [bagisto-06da5b920937474aa5682afece8e65e0.json](reports/bagisto-06da5b920937474aa5682afece8e65e0.json) | `passed` |
| Shopware 6.7.15.1 | 21 | [shopware-169394414b8a4d5180f8b5859fa77dce.json](reports/shopware-169394414b8a4d5180f8b5859fa77dce.json) | `passed`（已補測 `/checkout/gateway`） |
| Sylius Standard 2.2.4／核心 2.2.12 | 22 | [sylius-24210669ab954772890b8bfb2d54a449.json](reports/sylius-24210669ab954772890b8bfb2d54a449.json) | `passed` |

本次同時確認：證據遮蔽測試 6/6 通過、[privacy-audit.json](reports/privacy-audit.json) 通過、保護檔案 SHA-256 未變、active manifest 為 64 個操作（21+21+22）。Shopware 的 `/checkout/gateway` 已在隔離實例實測並通過回應結構斷言；Sylius 的 `/customers/verification-request` 因固定實例 live spec 沒有該路由且實機回 404，已從現行採用清單、參數文件與索引移除；原始規格快照仍保留作來源證據。`ready_for_collection` 仍保持 `false`。三平台容器在本次彙總後已停止，資料卷保留。

## 規格差異與接續紀錄

原有三份 API_parameters、原始契約、active manifest、Medusa 與 Mirage 均未覆寫。另存的 `upstream/` 包含固定來源與新匯出的規格；不直接取代既有文件。原 Bagisto 規格來源 commit 的 Composer 需求已是 PHP 8.4／Laravel 13，但固定的 2.4.10 核心是 PHP 8.3～8.4／Laravel 12；必須使用 API 2.4.4 的相容版本。21 個選定路徑／方法在該 release 快照均存在，這仍不等於部署驗證。

Shopware 原規格 `6.7.9999999-dev` 與實例 6.7.15.1 分開保存。Sylius 原規格 `0.0.0` 不當作平台版本。實際進度、資源紀錄與待處理問題另見 `reports/`，後續應先閱讀最近的執行摘要，再接續尚未通過的實測。

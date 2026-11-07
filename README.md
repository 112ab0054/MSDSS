# MSDSS

目前建立 Medusa 電商 API 與官方 Next.js 商城前台的實驗環境，尚未加入 XGBoost、攻擊偵測或欺敵功能。

## 服務入口

- 商城首頁：http://161.33.154.211:3000
- 顧客登入／註冊：http://161.33.154.211:3000/gb/account（選 Join us 註冊）
- 商品列表：http://161.33.154.211:3000/gb/store
- 管理介面：http://161.33.154.211:8000/app
- Swagger API 文件：http://161.33.154.211:8000/docs
- Store OpenAPI：http://161.33.154.211:8000/openapi/store
- Admin OpenAPI：http://161.33.154.211:8000/openapi/admin
- 健康檢查：http://161.33.154.211:8000/health

管理員登入資訊另外保存在本機 `.deployment/admin.json` 與主機同名檔案，不提交到 Git。

## 架構與版本

四個容器：Medusa 2.22.4、PostgreSQL 16、Redis 7、Next.js 16.4.5 商城前台。Medusa 同時執行 API、管理介面及背景工作，適用單機實驗環境。

商城使用 3000 埠，Medusa API 與管理後台使用 8000 埠。PostgreSQL 與 Redis 沒有對外發布連接埠。
資料庫、Redis 與上傳檔案使用獨立 Docker volumes，重啟容器不會清除資料。

`backend/src/scripts/seed.ts` 使用官方 starter 示範資料，包括商品、庫存、地區與銷售管道。
商城商品列表、關鍵字搜尋、排序與篩選使用官方 DTC starter 的 `product` 搜尋索引，定義在 `backend/src/search/`，並由 `backend/src/api/middlewares.ts` 開放給 Store API。
索引儲存在現有 PostgreSQL 中，服務啟動時填入商品，商品事件會持續同步；不需要額外的搜尋服務。
OpenAPI 取自 Medusa `v2.22.4` tag 的 bundled specifications；上游文件的 `info.version` 仍標示 `2.22.3`，此處保留原始版本欄位。
為使 Swagger 的 Try it out 操作目前部署，僅將 OpenAPI 的 server URL 設為同一來源 `/`。

## 在其他環境部署

需要 Docker 與 Docker Compose。此 Oracle 主機的 Compose 指令是 `docker-compose`；若你的版本使用 `docker compose`，將下列指令換成空格形式即可。

1. 複製 `.env.example` 為 `.env`，設定部署網址，並產生獨立且隨機的資料庫密碼、JWT secret 與 Cookie secret。資料庫密碼使用十六進位字元，避免 URL 編碼問題。
2. 執行：

   ```sh
   docker-compose build medusa
   docker-compose up -d postgres redis
   docker-compose run --rm medusa npm run migrate
   docker-compose run --rm medusa npm run seed
   docker-compose run --rm medusa npx medusa user -e YOUR_ADMIN_EMAIL -p YOUR_ADMIN_PASSWORD
   docker-compose up -d medusa
   ```

3. 在管理後台的 Settings > Publishable API Keys 取得已連結 Default Sales Channel 的 publishable key，填入 `.env` 的 `NEXT_PUBLIC_MEDUSA_PUBLISHABLE_KEY`。
4. 設定 `STOREFRONT_URL` 與預設地區（示範資料支援 `gb`），再執行：

   ```sh
   docker-compose build storefront
   docker-compose up -d storefront
   ```

商城的顧客帳號與管理員帳號分開。顧客在商城的 Account > Join us 自行註冊。
前台伺服器透過 Docker 內部網址 `http://medusa:9000` 呼叫 API；需要由瀏覽器發出的請求使用公開 API 網址。
`NEXT_PUBLIC_*` 變數會在建置時寫入前台，因此變更公開網址或 publishable key 後需重新 build 前台。

只在第一次初始化資料庫時執行 seed；不要每次部署都重複灌入示範資料。

既有環境新增或調整搜尋索引後，先重新 build 後端，再執行 `docker-compose run --rm medusa npx medusa db:migrate:search --execute-safe-search`，最後重新啟動後端。
此操作建立或更新搜尋索引，不會重新建立商品或清空原有商品資料。

## 維護

```sh
docker-compose ps
docker-compose logs --tail=100 medusa
docker-compose restart medusa
docker-compose stop
```

伺服器目錄為 `/home/ubuntu/MSDSS`。變更程式後重新 build，再執行 migrations 及 `up -d medusa`。

目前是使用 IP 的 HTTP 實驗環境。使用真實個資或正式帳密前，須設定網域與 HTTPS，並將 `COOKIE_SECURE` 改為 `true`。
備份資料庫後再進行版本升級；`docker-compose down -v` 會刪除持久化資料。

## 目錄

- `backend/`：Medusa、示範資料與 API 文件路由。
- `storefront/`：官方 DTC starter 的 Next.js 商城前台與 Docker 設定。
- `compose.yaml`：四個服務及持久化儲存設定。
- `.env.example`：環境變數範本，不含真正密碼。
- `THIRD_PARTY_NOTICES.md`：官方 starter 與 API 規格來源。

官方部署說明：https://docs.medusajs.com/learn/deployment/general

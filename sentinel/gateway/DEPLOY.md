# Medusa＋XGBoost Docker 部署

## 請求流向

```text
瀏覽器／商城伺服器 → gateway:8080 → medusa:9000
                        └─ 選用的 79 操作 → XGBoost（僅觀察）
```

對外網址維持 `http://161.33.154.211:8000`，商城維持 `:3000`。
Medusa 不再直接發布主機連接埠；管理介面、文件及清單外 API 也由 gateway 原樣轉送。
`/health` 由 gateway 轉給 Medusa，不屬於模型偵測目標。

模型包放在 `sentinel/gateway/model/`，映像同時帶入同版推論程式與 79 操作清單。
不需要訓練 CSV、Windows 路徑或雲端硬碟。模型 SHA／自測失敗時容器拒絕啟動。
啟動後推論失敗、逾時或忙碌，仍依既有觀察模式轉送並記警告；健康檢查不代表每筆都被分析。
目前模型仍有正常請求誤報，不啟用自動封鎖。

## 更新既有主機

先確認遠端專案位置、現有 Compose project 名稱及執行版本。保留既有 `.env`、
PostgreSQL、Redis、uploads volumes；不要執行 seed、`down -v` 或更換 project 名稱。
切換連接埠時 Medusa／商城會短暫重啟。

**上傳新檔案前**，在遠端原專案目錄建立私人備份：

```sh
umask 077
backup_dir=".deployment/before-gateway-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"
cp compose.yaml "$backup_dir/compose.yaml"
cp .env "$backup_dir/.env"
```

上傳更新後的 compose.yaml、sentinel/gateway、sentinel/model 的推論原始碼、
requirements.txt，以及 sentinel/analysis/api-extension/medusa-holdout-inventory.json。
不覆蓋 `.env`，不需要上傳資料集或測試報告。確認 PUBLIC_URL 仍是公開的 `:8000`，
MEDUSA_PORT 仍是 8000；PUBLIC_URL 不應改成 Docker 內部位址。

以下命令皆在遠端原專案目錄執行（舊版主機可將 `docker compose` 換為 `docker-compose`）：

```sh
docker compose config --quiet
docker compose build gateway
# 只在 gateway 成功建置後切換；沿用現有 Medusa、商城映像及資料。
docker compose up -d --no-build medusa gateway storefront
docker compose ps
docker compose logs --tail=80 gateway
curl -f http://127.0.0.1:8000/health
```

gateway 日誌應出現 `model_ready`，且 `mode=offline exploratory=True` 需如實保留。
再從商城操作商品、登入及購物車，確認出現 `prediction label=...`。
只查看健康檢查不足以證明商城的請求確實經過模型。
這些步驟不會重建 Medusa／商城映像；若遠端沒有現有映像，應先確認部署現況，不能當作更新直接執行。

## 回復原部署

將 backup_dir 換成前面實際備份目錄，在原專案目錄執行：

```sh
docker compose stop gateway
cp "$backup_dir/compose.yaml" compose.yaml
cp "$backup_dir/.env" .env
docker compose up -d --no-build medusa storefront
```

此操作保留資料 volumes；先停 gateway 才能讓舊 Medusa 重新使用主機 8000。
不使用 `--remove-orphans`，避免影響同專案中其他隊友模組。

## 本次部署狀態

本機 Docker 建置及實測結果見 docker-verification.json。
遠端尚未部署：目前環境未綁定 SSH 憑證，對 161.33.154.211 的 HTTP 請求被環境政策回覆
`Domain forbidden`。需安全設定 SSH 存取、帳號、專案目錄及目標主機的網路允許規則。
不得把私人 SSH key 或主機 `.env` 加入 Git。

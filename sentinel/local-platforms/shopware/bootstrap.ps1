$ErrorActionPreference = 'Stop'
$compose = Join-Path $PSScriptRoot 'compose.yaml'
$runtime = Join-Path $PSScriptRoot '../.runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
$container = docker compose -f $compose ps -q shopware
if (-not $container -or $LASTEXITCODE -ne 0) { throw '專用 Shopware 容器未啟動' }
$project = docker inspect $container --format '{{index .Config.Labels "com.docker.compose.project"}}'
if ($project -ne 'msdss-phase1-shopware') { throw '拒絕操作非本次測試容器' }
docker cp "$PSScriptRoot/bootstrap.php" "${container}:/tmp/msdss-bootstrap.php"
if ($LASTEXITCODE -ne 0) { throw '初始化程式複製失敗' }
$config = docker compose -f $compose exec -T shopware php /tmp/msdss-bootstrap.php
if ($LASTEXITCODE -ne 0) { throw '初始化失敗；沒有輸出憑證' }
# Capture the key without displaying it in logs.
try { $parsed = ($config -join "`n") | ConvertFrom-Json } catch { throw '初始化輸出無法解析；原始內容可能含憑證，不顯示於公開紀錄。' }
if (-not $parsed.access_key) { throw '沒有取得 storefront key' }
[IO.File]::WriteAllText((Join-Path $runtime 'shopware.json'), ($parsed | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
docker compose -f $compose exec -T shopware php bin/console cache:clear --no-interaction
if ($LASTEXITCODE -ne 0) { throw '快取清除失敗' }
Write-Output '本機通路設定完成；存取憑證僅保存在忽略提交的 .runtime 目錄。'

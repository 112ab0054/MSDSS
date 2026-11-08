param([Parameter(Mandatory)][ValidateSet('bagisto','sylius')][string]$Platform)
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/preflight.ps1"
$otherProjects = docker ps --format '{{.Label "com.docker.compose.project"}}'
if ($otherProjects | Where-Object { $_ -like 'msdss-phase1-*' -and $_ -ne "msdss-phase1-$Platform" }) {
  throw '另一個本次平台仍在執行，請先停止該平台'
}
& "$PSScriptRoot/prepare.ps1" -Platform $Platform
$runtime = Join-Path $PSScriptRoot '.runtime'
$marker = Join-Path $runtime "$Platform.initialized"
if (Test-Path $marker) { throw '已初始化，不重複安裝；請使用 manage.ps1 start' }
$compose = Join-Path $PSScriptRoot "$Platform/compose.yaml"
$source = Join-Path $runtime $Platform
Copy-Item "$PSScriptRoot/php/guard-empty.php" (Join-Path $source '.msdss-guard-empty.php')
Copy-Item "$PSScriptRoot/$Platform/seed.php" (Join-Path $source '.msdss-seed.php')
if ($Platform -eq 'bagisto') { Copy-Item "$PSScriptRoot/bagisto/setup-core.sh" (Join-Path $source '.msdss-setup-core.sh') }
$log = Join-Path $runtime "$Platform-install.log"
function Invoke-PrivateDocker([string[]]$Arguments) {
  & docker @Arguments >> $log 2>&1
  if ($LASTEXITCODE -ne 0) { throw "步驟失敗；原始安裝輸出僅保存在忽略提交的 .runtime/$Platform-install.log，檢查後須遮蔽才可分享。" }
}
Invoke-PrivateDocker @('compose','-f',$compose,'build','app')
Invoke-PrivateDocker @('compose','-f',$compose,'up','-d','--wait','db')
if ($Platform -eq 'bagisto') {
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','sh','.msdss-setup-core.sh')
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','sh','-c','mkdir -p storage/app/public storage/framework/cache/data storage/framework/sessions storage/framework/views storage/logs bootstrap/cache')
}
Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','.msdss-guard-empty.php',$Platform)
$locks = Join-Path $PSScriptRoot 'locks'
New-Item -ItemType Directory -Force $locks | Out-Null
$lock = Join-Path $locks "$Platform-composer.lock"
if (Test-Path $lock) {
  Copy-Item $lock (Join-Path $source 'composer.lock')
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','composer','install','--no-interaction','--prefer-dist','--no-progress','--no-scripts')
} else {
  # First resolution is retained immediately, even if a later installation step fails.
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','composer','update','--no-interaction','--prefer-dist','--no-progress','--no-scripts')
  Copy-Item (Join-Path $source 'composer.lock') $lock
}
if ($Platform -eq 'bagisto') {
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','composer','dump-autoload','--no-interaction')
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','artisan','bagisto:install','--no-interaction')
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','artisan','bagisto-api-platform:install','--no-interaction')
} else {
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','bin/console','lexik:jwt:generate-keypair','--skip-if-exists','--no-interaction')
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','bin/console','sylius:install','-s','default','--no-interaction')
}
$seedResult = docker compose -f $compose run --rm --no-deps app php .msdss-seed.php
if ($LASTEXITCODE -ne 0) { throw '測試種子建立失敗；沒有將憑證寫入公開紀錄' }
try { $config = ($seedResult -join "`n") | ConvertFrom-Json } catch { throw '種子設定輸出無法解析；原始內容可能含憑證，不顯示於公開紀錄。' }
[IO.File]::WriteAllText((Join-Path $runtime "$Platform.json"), ($config | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
if ($Platform -eq 'bagisto') {
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','artisan','indexer:index','--mode=full')
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','artisan','optimize:clear')
} else {
  Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','bin/console','cache:clear','--no-interaction')
}
Copy-Item (Join-Path $source 'composer.lock') (Join-Path $locks "$Platform-composer.lock")
[IO.File]::WriteAllText($marker, [DateTimeOffset]::Now.ToString('o'))
Write-Output '初始化及種子設定完成；這不代表正常流程通過。接著使用 manage.ps1 start 並執行對應流程程式。'

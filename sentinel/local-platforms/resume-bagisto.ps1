# Recover the observed API-installer cache timeout without running the database-wiping installer again.
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/preflight.ps1"
$runtime = Join-Path $PSScriptRoot '.runtime'
if (Test-Path "$runtime/bagisto.initialized") { throw '已完成初始化，不重複執行種子；請使用 manage.ps1 start' }
$compose = Join-Path $PSScriptRoot 'bagisto/compose.yaml'
Copy-Item "$PSScriptRoot/bagisto/seed.php" "$runtime/bagisto/.msdss-seed.php"
Copy-Item "$PSScriptRoot/bagisto/setup-core.sh" "$runtime/bagisto/.msdss-setup-core.sh"
$log = Join-Path $runtime 'bagisto-install.log'
function Invoke-PrivateDocker([string[]]$Arguments) {
  & docker @Arguments >> $log 2>&1
  if ($LASTEXITCODE -ne 0) { throw '續作失敗；請用 show-private-log.ps1 查看已遮蔽輸出，不要重跑安裝器。' }
}
Invoke-PrivateDocker @('compose','-f',$compose,'up','-d','--wait','db')
Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','sh','.msdss-setup-core.sh')
Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','sh','-c','mkdir -p storage/app/public storage/framework/cache/data storage/framework/sessions storage/framework/views storage/logs bootstrap/cache')
Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','artisan','optimize:clear')
$seed = docker compose -f $compose run --rm --no-deps app php .msdss-seed.php 2>> $log
if ($LASTEXITCODE -ne 0) { throw '種子建立失敗，沒有覆寫資料庫。' }
try { $parsed = ($seed -join "`n") | ConvertFrom-Json } catch { throw '種子輸出無法解析；可能含憑證，不顯示原始內容。' }
[IO.File]::WriteAllText("$runtime/bagisto.json", ($parsed | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','artisan','indexer:index','--mode=full')
Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','artisan','config:cache')
Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','app','php','artisan','route:cache')
[IO.File]::WriteAllText("$runtime/bagisto.initialized", [DateTimeOffset]::Now.ToString('o'))
Write-Output 'Bagisto 續作完成，尚須以真實 API 流程驗證。'

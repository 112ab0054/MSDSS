# All database writes are restricted to this dedicated Compose project.
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/preflight.ps1"
$other = docker ps --format '{{.Label "com.docker.compose.project"}}'
if ($other | Where-Object { $_ -like 'msdss-phase1-*' -and $_ -ne 'msdss-phase1-medusa' }) { throw '請先停止另一個本次驗證平台' }
$runtime = Join-Path $PSScriptRoot '.runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
$marker = Join-Path $runtime 'medusa.initialized'
if (Test-Path $marker) { throw '已初始化；請使用 manage.ps1 啟動，不重建資料' }
$envFile = Join-Path $runtime 'medusa.env'
if (!(Test-Path $envFile)) {
  function New-LocalSecret { [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant() }
  $dbPassword = New-LocalSecret
  $settings = @(
    'POSTGRES_DB=msdss_medusa_verify', 'POSTGRES_USER=msdss_medusa_verify', "POSTGRES_PASSWORD=$dbPassword",
    "DATABASE_URL=postgres://msdss_medusa_verify:${dbPassword}@db:5432/msdss_medusa_verify",
    'REDIS_URL=redis://redis:6379', 'PUBLIC_URL=http://127.0.0.1:18084',
    'STORE_CORS=http://127.0.0.1:18084', 'ADMIN_CORS=http://127.0.0.1:18084', 'AUTH_CORS=http://127.0.0.1:18084',
    "JWT_SECRET=$(New-LocalSecret)", "COOKIE_SECRET=$(New-LocalSecret)", 'COOKIE_SECURE=false', 'NODE_ENV=production'
  )
  [IO.File]::WriteAllLines($envFile, $settings, [Text.UTF8Encoding]::new($false))
}
$compose = Join-Path $PSScriptRoot 'medusa/compose.yaml'
$log = Join-Path $runtime 'medusa-install.log'
function Invoke-PrivateDocker([string[]]$Arguments) {
  & docker @Arguments >> $log 2>&1
  if ($LASTEXITCODE -ne 0) { throw 'Medusa 初始化步驟失敗；原始輸出僅保存在 .runtime/medusa-install.log，請遮蔽後查看。' }
}
Invoke-PrivateDocker @('compose','-f',$compose,'build','app')
Invoke-PrivateDocker @('compose','-f',$compose,'up','-d','--wait','db','redis')
$tables = docker compose -f $compose exec -T db psql -U msdss_medusa_verify -d msdss_medusa_verify -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"
if ($LASTEXITCODE -ne 0 -or ($tables -join '').Trim() -ne '0') { throw '隔離資料庫已有表或無法核對；拒絕重跑種子，不刪除或重灌資料。' }
foreach ($step in @(@('db:migrate'), @('db:migrate:search','--execute-safe-search'), @('exec','./src/scripts/seed.ts'))) {
  Invoke-PrivateDocker (@('compose','-f',$compose,'run','--rm','--no-deps','app','npx','medusa') + $step)
}
$fixture = Join-Path $PSScriptRoot 'medusa/catalog-fixture.ts'
Invoke-PrivateDocker @('compose','-f',$compose,'run','--rm','--no-deps','--volume',"${fixture}:/app/src/scripts/msdss-catalog-fixture.ts:ro",'app','npx','medusa','exec','./src/scripts/msdss-catalog-fixture.ts')
$key = docker compose -f $compose exec -T db psql -U msdss_medusa_verify -d msdss_medusa_verify -Atc "SELECT token FROM api_key WHERE type='publishable' AND revoked_at IS NULL LIMIT 1"
if ($LASTEXITCODE -ne 0 -or !($key -join '').Trim()) { throw '尚未取得種子建立的 storefront key，不顯示原始輸出。' }
$config = @{ publishable_api_key = ($key -join '').Trim() } | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $runtime 'medusa.json'), $config, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($marker, [DateTimeOffset]::Now.ToString('o'))
Write-Output 'Medusa 獨立資料庫初始化完成；接著啟動並執行 run_medusa.py。這不代表所有 API 已通過。'

param([Parameter(Mandatory)][ValidateSet('bagisto','sylius')][string]$Platform)
$ErrorActionPreference = 'Stop'
$versions = Get-Content "$PSScriptRoot/versions.json" -Raw | ConvertFrom-Json
$version = $versions.$Platform
$commit = if ($Platform -eq 'sylius') { $version.template_commit } else { $version.commit }
$runtime = Join-Path $PSScriptRoot '.runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
$source = Join-Path $runtime $Platform
if (-not (Test-Path -LiteralPath $source)) {
  git init --quiet $source
  if ($LASTEXITCODE -ne 0) { throw '無法建立獨立來源目錄' }
  git -C $source remote add origin $version.repository
}
$origin = git -C $source remote get-url origin
if ($origin -ne $version.repository) { throw '來源目錄的遠端不符，停止以避免覆寫其他資料' }
$head = git -C $source rev-parse --verify HEAD 2>$null
if (-not $head) {
  git -C $source -c http.lowSpeedLimit=1024 -c http.lowSpeedTime=60 fetch --quiet --depth 1 origin $commit
  if ($LASTEXITCODE -ne 0) { throw '固定版本下載失敗' }
  git -C $source checkout --quiet --detach FETCH_HEAD
  if ($LASTEXITCODE -ne 0) { throw '固定版本取出失敗' }
} elseif ($head -ne $commit) {
  throw '來源目錄已有不同版本，不自動重設或覆寫'
}
if ((git -C $source rev-parse HEAD) -ne $commit) { throw '來源 commit 核對失敗' }
if ($Platform -eq 'bagisto') {
  git -C $source archive --format=tar --output=.msdss-core.tar.tmp $commit packages
  if ($LASTEXITCODE -ne 0) { throw '固定核心封裝失敗' }
  Move-Item -LiteralPath (Join-Path $source '.msdss-core.tar.tmp') -Destination (Join-Path $source '.msdss-core.tar') -Force
  $archiveHash = (Get-FileHash (Join-Path $source '.msdss-core.tar')).Hash.ToLower()
  [IO.File]::WriteAllText((Join-Path $source '.msdss-core.tar.sha256'), "$archiveHash  .msdss-core.tar`n", [Text.UTF8Encoding]::new($false))
}
$envPath = Join-Path $runtime "$Platform.env"
if (-not (Test-Path -LiteralPath $envPath)) {
  $dbPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
  $rootPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
  $appSecret = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  $envText = @"
MYSQL_DATABASE=msdss_$Platform
MYSQL_USER=msdss_$Platform
MYSQL_PASSWORD=$dbPassword
MYSQL_ROOT_PASSWORD=$rootPassword
DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=msdss_$Platform
DB_USERNAME=msdss_$Platform
DB_PASSWORD=$dbPassword
MAIL_MAILER=log
MAILER_DSN=null://null
APP_SECRET=$appSecret
"@
  if ($Platform -eq 'bagisto') {
    $envText += "`nAPP_ENV=local`nAPP_DEBUG=false`nAPP_URL=http://127.0.0.1:18081`nAPP_LOCALE=en`nAPP_CURRENCY=USD`nSESSION_DRIVER=file`nCACHE_STORE=file`nQUEUE_CONNECTION=sync`n"
  } else {
    $envText += "`nAPP_ENV=dev`nAPP_DEBUG=0`nDATABASE_URL=mysql://msdss_${Platform}:$dbPassword@db:3306/msdss_${Platform}?serverVersion=mariadb-10.11.14&charset=utf8mb4`nJWT_PASSPHRASE=$appSecret`nSYLIUS_MESSENGER_TRANSPORT_MAIN_DSN=doctrine://default`nSYLIUS_MESSENGER_TRANSPORT_MAIN_FAILED_DSN=doctrine://default?queue_name=main_failed`nSYLIUS_MESSENGER_TRANSPORT_PAYMENT_REQUEST_DSN=sync://`nSYLIUS_MESSENGER_TRANSPORT_PAYMENT_REQUEST_FAILED_DSN=sync://`n"
  }
  [IO.File]::WriteAllText($envPath, $envText, [Text.UTF8Encoding]::new($false))
}
$composerPath = Join-Path $source 'composer.json'
$composer = Get-Content $composerPath -Raw | ConvertFrom-Json
if ($Platform -eq 'bagisto') {
  $composer.require | Add-Member -NotePropertyName 'bagisto/bagisto-api' -NotePropertyValue $version.api_version -Force
} else {
  $composer.require.'sylius/sylius' = $version.core_version
  $composer.require | Add-Member -NotePropertyName 'friendsofsymfony/rest-bundle' -NotePropertyValue $version.compatibility_dependencies.'friendsofsymfony/rest-bundle' -Force
}
[IO.File]::WriteAllText($composerPath, ($composer | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
if ($Platform -eq 'bagisto' -and -not (Test-Path (Join-Path $source '.env'))) {
  Copy-Item -LiteralPath (Join-Path $source '.env.example') -Destination (Join-Path $source '.env')
}
if ($Platform -eq 'bagisto') {
  # The installer reads .env directly, so align it with the isolated container environment.
  $appEnvPath = Join-Path $source '.env'
  $appEnv = Get-Content $appEnvPath -Raw
  foreach ($entry in (Get-Content $envPath)) {
    if ($entry -notmatch '^([A-Z_]+)=(.*)$') { continue }
    $key = $Matches[1]
    if ($key -like 'MYSQL_*') { continue }
    $line = $entry
    if ($appEnv -match "(?m)^$key=.*$") {
      $appEnv = [regex]::Replace($appEnv, "(?m)^$key=.*$", [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $line })
    } else { $appEnv += "`n$line" }
  }
  [IO.File]::WriteAllText($appEnvPath, $appEnv, [Text.UTF8Encoding]::new($false))
}
Write-Output "固定來源已備妥：$Platform @ $commit；尚未安裝相依、初始化資料庫或通過流程。"

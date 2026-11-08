param([Parameter(Mandatory)][ValidateSet('bagisto','shopware','sylius')][string]$Platform)
$ErrorActionPreference = 'Stop'
$manager = Join-Path $PSScriptRoot '../local-platforms/manage.ps1'
# Do not stop an already-running platform at the end unless this wrapper started it.
$running = @(docker ps --filter "label=com.docker.compose.project=msdss-phase1-$Platform" --format '{{.Names}}' 2>$null)
if ($LASTEXITCODE -ne 0) { throw 'Docker 引擎尚未就緒，沒有啟動或停止任何服務' }
$started = "msdss-phase1-$Platform-app-1" -notin $running
try {
  if ($started) { & $manager -Platform $Platform -Action start }
  & python "$PSScriptRoot/collect.py" --platform $Platform --execute
  if ($LASTEXITCODE -ne 0) { throw '試產未完整通過；已保存實際狀態與遮蔽證據，不重灌或補造資料' }
} finally {
  if ($started) {
    $after = @(docker ps --filter "label=com.docker.compose.project=msdss-phase1-$Platform" --format '{{.Names}}' 2>$null)
    if ($LASTEXITCODE -eq 0) {
      $newContainers = @($after | Where-Object { $_ -notin $running })
      if ($newContainers.Count -gt 0) { & docker stop @newContainers | Out-Null }
    }
  }
}

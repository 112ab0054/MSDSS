param(
  [Parameter(Mandatory)][ValidateSet('bagisto','shopware','sylius','medusa')][string]$Platform,
  [Parameter(Mandatory)][ValidateSet('start','stop','status')][string]$Action
)
$ErrorActionPreference = 'Stop'
$compose = Join-Path $PSScriptRoot "$Platform/compose.yaml"
if ($Action -eq 'start') {
  & "$PSScriptRoot/preflight.ps1" -MinimumDiskGiB 4
  $others = docker ps --filter 'label=com.docker.compose.project' --format '{{.Label "com.docker.compose.project"}}'
  $expected = "msdss-phase1-$Platform"
  if ($others | Where-Object { $_ -like 'msdss-phase1-*' -and $_ -ne $expected }) {
    throw '另一個本次測試平台仍在執行；請先使用 stop 停止該平台，逐一驗證。'
  }
  # Runtime start only. Downloading/building images must be done as a separate initialization step.
  docker compose -f $compose up -d --pull never --no-build
} elseif ($Action -eq 'stop') {
  docker compose -f $compose stop
} else {
  docker compose -f $compose ps
}
if ($LASTEXITCODE -ne 0) { throw "平台操作失敗：$Action" }

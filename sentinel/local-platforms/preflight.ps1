param([string]$OutputPath = "$PSScriptRoot/reports/preflight.json", [ValidateRange(3,100)][double]$MinimumDiskGiB = 6)
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$drive = Get-PSDrive C
$result = [ordered]@{
  checked_at = [DateTimeOffset]::Now.ToString('o')
  project = (Resolve-Path "$PSScriptRoot/../..").Path
  total_ram_gib = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
  free_ram_gib = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
  free_disk_gib = [math]::Round($drive.Free / 1GB, 2)
  docker_engine = $null
  docker_ready = $false
  wsl_available_gib = $null
  wsl_reclaimable_file_gib = $null
  effective_headroom_gib = $null
  required_headroom_gib = 2.25
  required_disk_gib = $MinimumDiskGiB
}
$job = Start-Job { docker version --format '{{.Server.Version}}' 2>$null }
try {
  if (Wait-Job $job -Timeout 15) {
    $version = (Receive-Job $job) -join ''
    if ($version -match '^\d+\.\d+\.\d+$') {
      $result.docker_engine = $version
      $result.docker_ready = $true
    }
  }
} finally { Stop-Job $job; Remove-Job $job }
if ($result.docker_ready) {
  $meminfo = (wsl -d docker-desktop -- cat /proc/meminfo) -join "`n"
  if ($LASTEXITCODE -eq 0) {
    $mem = @{}
    foreach ($line in ($meminfo -split "`n")) {
      if ($line -match '^(\w+):\s+(\d+) kB') { $mem[$Matches[1]] = [double]$Matches[2] }
    }
    $result.wsl_available_gib = [math]::Round($mem.MemAvailable / 1MB, 2)
    $result.wsl_reclaimable_file_gib = [math]::Round([math]::Max(0, ($mem.Buffers + $mem.Cached + $mem.SReclaimable - $mem.Shmem)) / 1MB, 2)
    $result.effective_headroom_gib = [math]::Round($result.free_ram_gib + [math]::Min($result.wsl_available_gib, $result.wsl_reclaimable_file_gib), 2)
  }
}
New-Item -ItemType Directory -Force (Split-Path $OutputPath) | Out-Null
$result | ConvertTo-Json | Set-Content -Encoding UTF8 $OutputPath
$result | ConvertTo-Json
if (-not $result.docker_ready) { throw 'Docker Linux 引擎未就緒；未啟動或變更任何平台。' }
# Shared runtime images have been measured separately. Reserve 6 GiB before the next operation.
if ($result.free_disk_gib -lt $result.required_disk_gib) { throw "C 槽不足 $MinimumDiskGiB GiB，暫停操作；不會自動清理資料。" }
# One platform is capped at 1.5 GiB; retain at least 0.75 GiB of headroom.
if ($result.free_ram_gib -lt 0.75 -or $null -eq $result.effective_headroom_gib -or $result.effective_headroom_gib -lt $result.required_headroom_gib -or $result.wsl_available_gib -lt 3) {
  throw '主機與 WSL 可回收檔案快取合計不足，暫停新增平台。'
}

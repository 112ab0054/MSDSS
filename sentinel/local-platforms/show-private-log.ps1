param([Parameter(Mandatory)][ValidateSet('bagisto','sylius','medusa','php-build','medusa-build')][string]$Name, [int]$Tail = 20)
$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.runtime'
$file = if ($Name -like '*-build') { Join-Path $runtime "$Name.log" } else { Join-Path $runtime "$Name-install.log" }
$text = (Get-Content -LiteralPath $file -Tail $Tail) -join "`n"
$envFiles = @((Join-Path $runtime 'bagisto.env'),(Join-Path $runtime 'sylius.env'),(Join-Path $runtime 'medusa.env'),(Join-Path $runtime 'bagisto/.env'))
foreach ($envFile in $envFiles) {
  if (-not (Test-Path -LiteralPath $envFile)) { continue }
  foreach ($line in (Get-Content -LiteralPath $envFile)) {
    if ($line -match '^(?:[A-Z_]*(?:PASSWORD|SECRET|TOKEN|KEY|DSN)[A-Z_]*)=(.+)$') {
      $value = $Matches[1].Trim('"')
      if ($value.Length -ge 6) { $text = $text.Replace($value, '[REDACTED]').Replace([uri]::EscapeDataString($value), '[REDACTED]') }
    }
  }
}
$text -split "`n" | ForEach-Object {
  if ($_ -match '(?i)password\s*[:=]|credential\s*[:=]|mysql://|mariadb://|postgres(?:ql)?://|Bearer\s+\S+') { '[REDACTED sensitive log line]' } else { $_ }
}

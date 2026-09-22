# 一条命令跑真实评测（提供商配置见 configs/providers.yaml，密钥在 .env.local）
# 例：
#   powershell -File scripts/run_real.ps1 zhipu:glm-5.3-flash -Workers 50
#   powershell -File scripts/run_real.ps1 deepseek:deepseek-flash -Workers 50 -Out reports/runs/ds-x
#   powershell -File scripts/run_real.ps1 zhipu:glm-5.3-flash -Tasks cit_validity -Effort max

param(
    [Parameter(Mandatory = $true)][string]$Model,
    [int]$Workers = 50,
    [string]$Tasks = "cit_validity,u_element_extract,s_charge_subsume,contract_risk,a_irac_reason,long_horizon_case",
    [string]$Out = "",
    [string]$Effort = "",
    [double]$Temperature = -1
)
$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
if (-not $root) { $root = "D:\Claudeworkspace\cn-judbench" }
Set-Location $root

# 载入 .env.local（若存在）
$envFile = Join-Path $root ".env.local"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $l = $_.Trim()
        if ($l -and -not $l.StartsWith("#") -and $l.Contains("=")) {
            $k, $v = $l.Split("=", 2)
            Set-Item -Path "Env:$($k.Trim())" -Value $v.Trim().Trim('"').Trim("'")
        }
    }
}

if (-not $Out) {
    $slug = ($Model -replace "[:/]", "-")
    $Out = "reports/runs/$slug-c$Workers"
}
$py = Join-Path $root ".venv\Scripts\python.exe"
$pyArgs = @(
    "-m", "cnjudbench", "run-all",
    "--tasks", $Tasks,
    "--model", $Model,
    "--concurrency", "$Workers",
    "--out", $Out
)
if ($Effort) { $pyArgs += @("--reasoning-effort", $Effort) }
if ($Temperature -ge 0) { $pyArgs += @("--temperature", "$Temperature") }

Write-Host "RUN $Model workers=$Workers out=$Out"
& $py @pyArgs

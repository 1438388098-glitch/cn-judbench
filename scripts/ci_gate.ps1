# CI 门禁（impl-P1-rest §5）PowerShell 版：validate → pytest → mock run-all → 断言 → 翻转率。
# 任一步失败即 exit 1。CI 只跑 Mock，不烧真 API、不需要任何密钥。
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$PY = if ($env:PYTHON) { $env:PYTHON } else { "python" }

function Invoke-Step([string]$Title, [string[]]$CmdArgs) {
    Write-Host "== $Title =="
    & $PY @CmdArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "CI GATE: FAIL（$Title exit $LASTEXITCODE）"
        exit $LASTEXITCODE
    }
}

Invoke-Step "[1/5] validate" @("-m", "cnjudbench", "validate", "--items", "data/public", "--tasks", "tasks")
Invoke-Step "[2/5] pytest" @("-m", "pytest", "-q")
Invoke-Step "[3/5] run-all (mock:gold, with-judge)" @(
    "-m", "cnjudbench", "run-all",
    "--tasks", "cit_validity,u_element_extract,s_charge_subsume",
    "--model", "mock:gold", "--with-judge", "--judge", "mock",
    "--out", "reports/runs/ci"
)
Invoke-Step "[4/5] assert run gate" @("scripts/assert_run_gate.py", "reports/runs/ci")
Invoke-Step "[5/5] flip rate (mock 必须 0)" @("scripts/flip_rate_check.py")

Write-Host "CI GATE: ALL GREEN"

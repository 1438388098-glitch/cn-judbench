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

Invoke-Step "[1/7] validate" @("-m", "cnjudbench", "validate", "--items", "data/public", "--tasks", "tasks")
Invoke-Step "[2/7] pytest" @("-m", "pytest", "-q")
Invoke-Step "[3/7] run-all (mock:gold, with-judge)" @(
    "-m", "cnjudbench", "run-all",
    "--tasks", "cit_validity,u_element_extract,s_charge_subsume,a_irac_reason",
    "--model", "mock:gold", "--with-judge", "--judge", "mock",
    "--out", "reports/runs/ci"
)
Invoke-Step "[4/7] L2 mock:tools (t-fake-001)" @(
    "-m", "cnjudbench", "run",
    "--task", "tool_search_statute",
    "--model", "mock:tools",
    "--out", "reports/runs/ci-l2"
)
$pyAssert = @'
import json
from pathlib import Path
text = Path("reports/runs/ci-l2/summary.json").read_text(encoding="utf-8")
assert "t-fake-001" in text or "fake_tool" in text
# 负例应得 0.00
s = json.loads(text)
blob = json.dumps(s, ensure_ascii=False)
assert '"id": "t-fake-001"' in blob or "'t-fake-001'" in blob or "t-fake-001" in blob
print("L2 fake_tool gate: checked")
'@
& $PY -c $pyAssert
if ($LASTEXITCODE -ne 0) { Write-Host "CI GATE: FAIL（L2 assert）"; exit $LASTEXITCODE }
Invoke-Step "[5/7] assert run gate" @("scripts/assert_run_gate.py", "reports/runs/ci")
Invoke-Step "[6/7] flip rate (mock 必须 0)" @("scripts/flip_rate_check.py")

# [7/7] n-gram 污染双检接线（--ngram-corpus 实测生效）
$gateTmp = Join-Path ([System.IO.Path]::GetTempPath()) ("cjdb-gate-" + [guid]::NewGuid().ToString("N"))
Invoke-Step "[7/7a] export prompts" @("scripts/export_prompts.py", "--tasks", "cit_validity", "--run-dir", $gateTmp)
Get-Content (Join-Path $gateTmp "prompts/*.txt") -Raw | Set-Content (Join-Path $gateTmp "corpus.txt") -Encoding UTF8
Invoke-Step "[7/7b] run-all --ngram-corpus" @(
    "-m", "cnjudbench", "run-all",
    "--tasks", "cit_validity", "--model", "mock:gold",
    "--out", (Join-Path $gateTmp "run"),
    "--ngram-corpus", (Join-Path $gateTmp "corpus.txt")
)
$pyNg = @'
import json, sys
from pathlib import Path
s = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ng = s["contamination"]["ngram_overlap"]
assert ng["n"] == 8 and ng["max_overlap"] > 0.5, f"题面本源命中语料应高重叠: {ng}"
print(f"ngram wiring gate: max_overlap={ng['max_overlap']:.2f} top={ng['top_item']}")
'@
& $PY -c $pyNg (Join-Path $gateTmp "run/summary.json")
if ($LASTEXITCODE -ne 0) { Write-Host "CI GATE: FAIL（ngram assert）"; exit $LASTEXITCODE }
Remove-Item -Recurse -Force $gateTmp

Write-Host "CI GATE: ALL GREEN"

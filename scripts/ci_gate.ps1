# CI 门禁（impl-P1-rest §5）PowerShell 版：validate → pytest → mock run-all → 断言 → 翻转率。
# 任一步失败即 exit 1。CI 只跑 Mock，不烧真 API、不需要任何密钥。
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$PY = if ($env:PYTHON) { $env:PYTHON } else { "python" }

function Invoke-Step([string]$Title, [string[]]$CmdArgs) {
    Write-Host "== $Title =="
    & $PY @CmdArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "CI GATE: FAIL ($Title exit $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

Invoke-Step "[1/9] validate" @("-m", "cnjudbench", "validate", "--items", "data/public", "--tasks", "tasks")
Invoke-Step "[2/9] pytest" @("-m", "pytest", "-q")
Invoke-Step "[3/9] run-all (mock:gold, with-judge)" @(
    "-m", "cnjudbench", "run-all",
    "--tasks", "cit_validity,u_element_extract,s_charge_subsume,a_irac_reason",
    "--model", "mock:gold", "--with-judge", "--judge", "mock",
    "--out", "reports/runs/ci"
)
Invoke-Step "[4/9] L2 mock:tools (t-fake-001)" @(
    "-m", "cnjudbench", "run",
    "--task", "tool_search_statute",
    "--model", "mock:tools",
    "--out", "reports/runs/ci-l2"
)
$pyAssert = @'
import json
from pathlib import Path
s = json.loads(Path("reports/runs/ci-l2/summary.json").read_text(encoding="utf-8"))
# 与 ci_gate.sh 同强度：负例 t-fake-001 必须在场且 0 分（找不到即失败）
rows = list((s.get("per_item") or s.get("items") or [])
            + [x for t in (s.get("tasks") or {}).values() for x in t.get("items", [])])
hit = [r for r in rows if isinstance(r, dict) and r.get("id") == "t-fake-001"]
assert hit, "summary missing negative fixture t-fake-001"
row = hit[0]
assert row.get("score") in (0, 0.0, "0.00") or row.get("display") == "0.00", row
print("L2 fake_tool gate: checked (negative present, score 0.00)")
'@
$pyAssert | & $PY -
if ($LASTEXITCODE -ne 0) { Write-Host "CI GATE: FAIL (L2 assert)"; exit $LASTEXITCODE }
# [4b/9] v0.4 新任务 mock 管线（c391：与 ci_gate.sh 步骤对齐，消除本地门禁分叉）
Invoke-Step "[4b/9] v0.4 mock pipeline (dms+fault)" @(
    "-m", "cnjudbench", "run-all",
    "--tasks", "dms_side_effect_intake,tool_fault_recovery",
    "--model", "mock:tools",
    "--out", "reports/runs/ci-v04"
)
$pyV04 = @'
import json
from pathlib import Path
s = json.loads(Path("reports/runs/ci-v04/summary.json").read_text(encoding="utf-8"))
NEGATIVE_IDS = {"d-fake-001", "t-fake-001"}
for tid, task in s.get("tasks", {}).items():
    for row in task.get("items", []):
        sc = float(row["score"])
        if row["id"] in NEGATIVE_IDS:
            assert sc == 0.0, f"{row['id']} negative expected 0: {row['score']}"
        else:
            assert sc == 100.0, f"{row['id']} mock 重放应满分: {row['score']}"
print("v0.4 tasks mock gate: all 100")
'@
$pyV04 | & $PY -
if ($LASTEXITCODE -ne 0) { Write-Host "CI GATE: FAIL (4b assert)"; exit $LASTEXITCODE }

# [4c/9] 金样自证全覆盖：非工具 5 包 + 12 包自证矩阵完整性
Invoke-Step "[4c/9] gold self-proof 5 tasks" @(
    "-m", "cnjudbench", "run-all",
    "--tasks", "calc_fail_to_pass,gaia_fee_deadline,contract_risk,tau_jud_intake,long_horizon_case",
    "--model", "mock:gold",
    "--out", "reports/runs/ci-gold-all"
)
$pyGold = @'
import json
from pathlib import Path
s = json.loads(Path("reports/runs/ci-gold-all/summary.json").read_text(encoding="utf-8"))
for tid, task in s.get("tasks", {}).items():
    for row in task.get("items", []):
        assert float(row["score"]) == 100.0, \
            f"gold self-proof failed {tid}/{row['id']} = {row['score']}"
ALL = set()
for d in ("reports/runs/ci", "reports/runs/ci-l2",
          "reports/runs/ci-v04", "reports/runs/ci-gold-all"):
    sp = Path(d) / "summary.json"
    assert sp.is_file(), f"{d} 缺 summary.json"
    ALL |= set(json.loads(sp.read_text(encoding="utf-8")).get("tasks", {}))
EXPECT = {"cit_validity", "u_element_extract", "s_charge_subsume", "a_irac_reason",
          "tool_search_statute", "dms_side_effect_intake", "tool_fault_recovery",
          "calc_fail_to_pass", "gaia_fee_deadline", "contract_risk",
          "tau_jud_intake", "long_horizon_case"}
assert ALL == EXPECT, f"12 包自证矩阵不完整：缺 {EXPECT - ALL} 多 {ALL - EXPECT}"
print(f"self-proof matrix: {len(ALL)}/12 packages covered")
'@
$pyGold | & $PY -
if ($LASTEXITCODE -ne 0) { Write-Host "CI GATE: FAIL (4c assert)"; exit $LASTEXITCODE }

Invoke-Step "[5/9] assert run gate" @("scripts/assert_run_gate.py", "reports/runs/ci")
Invoke-Step "[6/9] flip rate (mock must be 0)" @("scripts/flip_rate_check.py")

# [7/9] 换答对齐 guard + file: 回灌全管线（demo_pipeline 等价流程；R14/R20 事故防线入 Gate）
$demoTmp = Join-Path ([System.IO.Path]::GetTempPath()) ("cjdb-demo-" + [guid]::NewGuid().ToString("N"))
Invoke-Step "[7/9a] export prompts" @("scripts/export_prompts.py", "--tasks", "u_element_extract", "--run-dir", (Join-Path $demoTmp "run"))
$pyFill = @'
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
index = json.loads((run / "index.json").read_text(encoding="utf-8"))
assert index, "index.json empty"
for entry in index:
    (run / entry["answer_file"]).write_text(
        json.dumps({"note": "ci gate placeholder answer"}, ensure_ascii=False),
        encoding="utf-8")
print(f"answers filled {len(index)} (placeholder)")
'@
$pyFill | & $PY - (Join-Path $demoTmp "run")
if ($LASTEXITCODE -ne 0) { Write-Host "CI GATE: FAIL (answers fill)"; exit $LASTEXITCODE }
Invoke-Step "[7/9b] answer alignment guard" @("scripts/check_answer_alignment.py", "--run-dir", (Join-Path $demoTmp "run"))
Invoke-Step "[7/9c] file: replay scoring" @("-m", "cnjudbench", "run", "--task", "u_element_extract", "--model", ("file:" + (Join-Path $demoTmp "run/answers")), "--out", (Join-Path $demoTmp "scored"))
$pyDemo = @'
import json, sys
from pathlib import Path
for f in ("manifest.json", "summary.json", "limits.md", "report.csv"):
    assert (Path(sys.argv[1]) / f).is_file(), f"missing artifact {f}"
s = json.loads((Path(sys.argv[1]) / "summary.json").read_text(encoding="utf-8"))
assert s["schema_version"] == "0.6"
print(f"file replay tasks={len(s.get('tasks', {}))} schema={s['schema_version']}")
'@
$pyDemo | & $PY - (Join-Path $demoTmp "scored")
if ($LASTEXITCODE -ne 0) { Write-Host "CI GATE: FAIL (file replay artifacts)"; exit $LASTEXITCODE }
Remove-Item -Recurse -Force $demoTmp

# [8/9] n-gram 污染双检接线（--ngram-corpus 实测生效）
$gateTmp = Join-Path ([System.IO.Path]::GetTempPath()) ("cjdb-gate-" + [guid]::NewGuid().ToString("N"))
Invoke-Step "[8/9a] export prompts" @("scripts/export_prompts.py", "--tasks", "cit_validity", "--run-dir", $gateTmp)
Get-Content (Join-Path $gateTmp "prompts/*.txt") -Raw | Set-Content (Join-Path $gateTmp "corpus.txt") -Encoding UTF8
Invoke-Step "[8/9b] run-all --ngram-corpus" @(
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
assert ng["n"] == 8 and ng["max_overlap"] > 0.5, f"prompt-source corpus should hit high overlap: {ng}"
print(f"ngram wiring gate: max_overlap={ng['max_overlap']:.2f} top={ng['top_item']}")
'@
$pyNg | & $PY - (Join-Path $gateTmp "run/summary.json")
if ($LASTEXITCODE -ne 0) { Write-Host "CI GATE: FAIL (ngram assert)"; exit $LASTEXITCODE }
Remove-Item -Recurse -Force $gateTmp

# [9/9] 锚×as_of 审计（与 ci_gate.sh 对齐）
Invoke-Step "[9/9] anchor x as_of audit" @("scripts/audit_anchors.py")

Write-Host "CI GATE: ALL GREEN"

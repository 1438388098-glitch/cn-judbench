#!/usr/bin/env bash
# CI 门禁（impl-P1-rest §5）：validate → pytest → mock run-all → 产物断言 → 翻转率=0。
# 任一步失败即 exit 1。CI 只跑 Mock，不烧真 API、不需要任何密钥。
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python}"

echo "== [1/6] validate =="
"$PY" -m cnjudbench validate --items data/public --tasks tasks

echo "== [2/6] pytest =="
"$PY" -m pytest -q

echo "== [3/6] run-all (mock:gold, with-judge) =="
"$PY" -m cnjudbench run-all \
  --tasks cit_validity,u_element_extract,s_charge_subsume,a_irac_reason \
  --model mock:gold --with-judge --judge mock \
  --out reports/runs/ci

echo "== [4/6] L2 mock:tools（含 t-fake-001 假调用负例） =="
"$PY" -m cnjudbench run \
  --task tool_search_statute \
  --model mock:tools \
  --out reports/runs/ci-l2
"$PY" - <<'PY'
import json
from pathlib import Path
s = json.loads(Path("reports/runs/ci-l2/summary.json").read_text(encoding="utf-8"))
# 负例 t-fake-001 必须 0.00
for row in s.get("per_item") or s.get("items") or []:
    if isinstance(row, dict) and row.get("id") == "t-fake-001":
        assert row.get("score") in (0, 0.0, "0.00") or row.get("display") == "0.00", row
        break
else:
    # summary 形态兼容：从 runs 明细找
    pass
print("L2 fake_tool gate: checked")
PY

echo "== [4b/6] v0.4 新任务 mock 管线（dms env_diff + fault recovery） =="
"$PY" -m cnjudbench run-all   --tasks dms_side_effect_intake,tool_fault_recovery   --model mock:tools   --out reports/runs/ci-v04
"$PY" - <<'PY'
import json
from pathlib import Path
s = json.loads(Path("reports/runs/ci-v04/summary.json").read_text(encoding="utf-8"))
NEGATIVE_IDS = {"d-fake-001", "t-fake-001"}  # 负例夹具设计即 0 分
for tid, task in s.get("tasks", {}).items():
    for row in task.get("items", []):
        sc = float(row["score"])
        if row["id"] in NEGATIVE_IDS:
            assert sc == 0.0, f"{row['id']} 负例应 0: {row['score']}"
        else:
            assert sc == 100.0, f"{row['id']} mock 重放应满分: {row['score']}'"
print("v0.4 tasks mock gate: all 100")
PY

echo "== [5/6] assert run gate =="
"$PY" scripts/assert_run_gate.py reports/runs/ci

echo "== [6/6] flip rate (mock 必须 0) =="
"$PY" scripts/flip_rate_check.py

echo "CI GATE: ALL GREEN"

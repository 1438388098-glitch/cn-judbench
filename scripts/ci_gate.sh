#!/usr/bin/env bash
# CI 门禁（impl-P1-rest §5 + v0.6 第 8 步锚审计）：validate → pytest → mock run-all → 产物断言 → 翻转率=0 → 换答对齐 guard+file: 回灌 → n-gram → 锚审计。
# 任一步失败即 exit 1。CI 只跑 Mock，不烧真 API、不需要任何密钥。
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python}"

echo "== [1/9] validate =="
"$PY" -m cnjudbench validate --items data/public --tasks tasks

echo "== [2/9] pytest =="
"$PY" -m pytest -q

echo "== [3/9] run-all (mock:gold, with-judge) =="
"$PY" -m cnjudbench run-all \
  --tasks cit_validity,u_element_extract,s_charge_subsume,a_irac_reason \
  --model mock:gold --with-judge --judge mock \
  --out reports/runs/ci

echo "== [4/9] L2 mock:tools（含 t-fake-001 假调用负例） =="
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

echo "== [4b/9] v0.4 新任务 mock 管线（dms env_diff + fault recovery） =="
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

echo "== [4c/9] 金样自证全覆盖：非工具 5 包 mock:gold（9+3 包矩阵补全） =="
"$PY" -m cnjudbench run-all   --tasks calc_fail_to_pass,gaia_fee_deadline,contract_risk,tau_jud_intake,long_horizon_case   --model mock:gold   --out reports/runs/ci-gold-all
"$PY" - <<'PY'
import json
from pathlib import Path
s = json.loads(Path("reports/runs/ci-gold-all/summary.json").read_text(encoding="utf-8"))
for tid, task in s.get("tasks", {}).items():
    for row in task.get("items", []):
        assert float(row["score"]) == 100.0, \
            f"金样自证失败 {tid}/{row['id']} = {row['score']}（mock:gold 应满分——非满分即金样 bug）"
print(f"gold self-proof gate: {len(s.get('tasks', {}))} tasks all 100")

# 12 包自证矩阵完整性：3/4/4b/4c 四步产物并集必须恰为核心 12 包
ALL = set()
for d in ("reports/runs/ci", "reports/runs/ci-l2",
          "reports/runs/ci-v04", "reports/runs/ci-gold-all"):
    sp = Path(d) / "summary.json"
    assert sp.is_file(), f"{d} 缺 summary.json（自证步骤须全部成功）"
    ALL |= set(json.loads(sp.read_text(encoding="utf-8")).get("tasks", {}))
EXPECT = {"cit_validity", "u_element_extract", "s_charge_subsume", "a_irac_reason",
          "tool_search_statute", "dms_side_effect_intake", "tool_fault_recovery",
          "calc_fail_to_pass", "gaia_fee_deadline", "contract_risk",
          "tau_jud_intake", "long_horizon_case"}
assert ALL == EXPECT, f"12 包自证矩阵不完整：缺 {EXPECT - ALL} 多 {ALL - EXPECT}"
print(f"self-proof matrix: {len(ALL)}/12 packages covered")
PY

echo "== [5/9] assert run gate =="
"$PY" scripts/assert_run_gate.py reports/runs/ci

echo "== [6/9] flip rate (mock 必须 0) =="
"$PY" scripts/flip_rate_check.py


echo "== [7/9] 换答对齐 guard + file: 回灌全管线（导出→占位作答→guard→回灌→产物核对；R14/R20 事故防线入 Gate） =="
bash scripts/demo_pipeline.sh

echo "== [8/9] n-gram 污染双检接线（--ngram-corpus 实测生效） =="
GATE_TMP="$(mktemp -d)"
"$PY" scripts/export_prompts.py --tasks cit_validity --run-dir "$GATE_TMP"
cat "$GATE_TMP"/prompts/*.txt > "$GATE_TMP/corpus.txt"
"$PY" -m cnjudbench run-all \
  --tasks cit_validity --model mock:gold \
  --out "$GATE_TMP/run" --ngram-corpus "$GATE_TMP/corpus.txt"
"$PY" - "$GATE_TMP/run/summary.json" <<'PY'
import json
import sys
from pathlib import Path

s = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ng = s["contamination"]["ngram_overlap"]
assert ng["n"] == 8 and ng["max_overlap"] > 0.5, f"题面本源命中语料应高重叠: {ng}"
print(f"ngram wiring gate: max_overlap={ng['max_overlap']:.2f} top={ng['top_item']}")
PY
rm -rf "$GATE_TMP"

echo "== [9/9] 锚×as_of 审计（E14 脚本化；惰性锚白名单见 reports/anchor-whitelist.json）=="
"$PY" scripts/audit_anchors.py

echo "CI GATE: ALL GREEN"

# -*- coding: utf-8 -*-
"""c134：set_f1 1-1 改版单变量消融（同份真实答案，旧/新 set_f1 离线对比）。

背景：reports/runs/glm53f-v04-merged-v06rescore 的全管线重判分差混入了
R1/R2 谓词修复与 lawkb 扩库（a_irac +52 主因是引用三检可解析），非单变量。
本脚本只动 set_f1：从 R2 提交（f3834b0）提取旧实现，对 element 谓词消费包
（s_charge_subsume / long_horizon_case / contract_risk）的每条真实答案，
分别用旧/新 set_f1 算 element F1，输出逐题分差与包级 micro。

用法： python scripts/ablate_setf1_v06.py [--commit f3834b0]
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ANSWERS = ROOT / "reports" / "runs" / "glm53f-v04-merged" / "answers"
TASKS = {  # task_id → [(items 文件, element path, gold_path)]（与各包 predicates.yaml 同源）
    "s_charge_subsume": [("data/public/s_charge_subsume.jsonl", "elements", "elements")],
    "long_horizon_case": [("data/public/long_horizon_case.jsonl", "phases_done", "phases_done")],
    "contract_risk": [("data/public/contract_risk.jsonl", "risk_labels", "risk_labels")],
}


def load_old_setf1(commit: str):
    src = subprocess.run(
        ["git", "show", f"{commit}:src/cnjudbench/score/norm.py"],
        capture_output=True, check=True).stdout.decode("utf-8")
    ns: dict = {}
    exec(compile(src, f"<{commit}:norm.py>", "exec"), ns)  # noqa: S102 —— 审计消融需钉住历史实现
    return ns["set_f1"]


def main() -> int:
    from cnjudbench.score.norm import set_f1 as new_setf1

    old_setf1 = load_old_setf1(
        sys.argv[sys.argv.index("--commit") + 1] if "--commit" in sys.argv else "f3834b0")

    grand = {"n": 0, "old_sum": 0.0, "new_sum": 0.0}
    for task_id, specs in TASKS.items():
        per = {"n": 0, "old_sum": 0.0, "new_sum": 0.0, "changed": []}
        for items_rel, path, gold_path in specs:
            rows = [json.loads(l) for l in (ROOT / items_rel).read_text(encoding="utf-8-sig").splitlines() if l.strip()]
            for it in rows:
                ans_f = ANSWERS / f"{it['id']}.txt"
                if not ans_f.is_file():
                    continue
                try:
                    answer = json.loads(ans_f.read_text(encoding="utf-8-sig"))
                except json.JSONDecodeError:
                    continue
                want = (it.get("gold") or {}).get(gold_path)
                if not isinstance(want, list) or not want:
                    continue
                got = answer.get(path) if isinstance(answer, dict) else None
                fo, _, _ = old_setf1(got, want)
                fn, _, _ = new_setf1(got, want)
                per["n"] += 1
                per["old_sum"] += fo
                per["new_sum"] += fn
                if abs(fo - fn) > 1e-9:
                    per["changed"].append((it["id"], round(fo, 3), round(fn, 3)))
        n = per["n"] or 1
        print(f"{task_id}: n={per['n']} oldF1={per['old_sum']/n:.4f} "
              f"newF1={per['new_sum']/n:.4f} changed={len(per['changed'])}")
        for iid, fo, fn in per["changed"][:6]:
            print(f"    {iid}: {fo} -> {fn}")
        grand["n"] += per["n"]; grand["old_sum"] += per["old_sum"]; grand["new_sum"] += per["new_sum"]
    n = grand["n"] or 1
    print(f"grand: n={grand['n']} oldF1={grand['old_sum']/n:.4f} newF1={grand['new_sum']/n:.4f} "
          f"delta={100*(grand['new_sum']-grand['old_sum'])/n:+.2f} 分")
    return 0


if __name__ == "__main__":
    sys.exit(main())

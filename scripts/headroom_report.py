# -*- coding: utf-8 -*-
"""扩题/削题余量报告（c252）：数据驱动回答「哪些包还有区分度余量」。

每个任务包聚合三个信号：
- 饱和率（saturation_flag 占比，作者侧「头部模型全分」标注）；
- rules 基线（无知识策略得分，判分可被刷分满足的程度）；
- 实证通过率（双考生 p，仅有 run 数据的包可算）。

输出 reports/headroom-report.md：饱和率高且实证 p 高的包 = 无余量，新增题
应注入到这些包的未饱和维度或直接新建包；rules 高的包先修判分再加题。

用法：python scripts/headroom_report.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

OUT = REPO / "reports" / "headroom-report.md"
MANIFEST = REPO / "data" / "public" / "MANIFEST.json"
BASELINE_RUN = REPO / "reports" / "runs" / "baseline-v06"


def main() -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    baseline = json.loads((BASELINE_RUN / "summary.json").read_text(encoding="utf-8"))
    rules_pt = (baseline.get("baselines") or {}).get("rules", {}).get("per_task", {})

    # 实证 p（双考生，仅有数据的题）
    emp_p: dict[str, float] = {}
    emp_json = REPO / "reports" / "difficulty_emp.json"
    if emp_json.is_file():
        for iid, v in json.loads(emp_json.read_text(encoding="utf-8"))["items"].items():
            emp_p[iid] = v["p"]

    rows = []
    for pkg, block in sorted(man["packages"].items()):
        items = block["items"]
        n = len(items)
        n_sat = sum(1 for it in items.values() if it.get("saturation_flag"))
        sat_rate = n_sat / n
        rules = float(rules_pt.get(pkg, 0) or 0)
        p_vals = [emp_p[i] for i in items if i in emp_p]
        emp = sum(p_vals) / len(p_vals) if p_vals else None
        headroom = "低" if (sat_rate >= 0.3 and (emp is None or emp >= 0.6)) \
            else ("中" if sat_rate >= 0.15 else "高")
        rows.append((pkg, n, sat_rate, rules, emp, headroom))

    lines = [
        "# 扩题/削题余量报告（scripts/headroom_report.py 自动生成）",
        "",
        "信号：饱和率 = saturation_flag 占比（作者侧头部全分标注）；rules = 无知识",
        "策略得分；实证 p = 双考生通过率（仅有 run 数据的题）。余量判定：",
        "饱和率≥30% 且实证 p≥60% → 低（优先新增该维度难题）；否则 ≥15% → 中；其余 → 高。",
        "",
        "| 任务包 | n | 饱和率 | rules 基线 | 实证 p | 扩题余量 |",
        "|---|---|---|---|---|---|",
    ]
    for pkg, n, sat_rate, rules, emp, headroom in rows:
        emp_s = f"{100 * emp:.2f}%" if emp is not None else "n/a"
        lines.append(f"| {pkg} | {n} | {100 * sat_rate:.1f}% | {rules:.2f} | {emp_s} | {headroom} |")

    low = [r[0] for r in rows if r[5] == "低"]
    lines += ["",
              "## 建议", ""]
    if low:
        lines.append(f"- 余量低的包（{', '.join(low)}）：新题注入其**未饱和维度**"
                     "（capability 复合维或更高 interaction 级），或直接新建包；")
    lines.append("- rules ≥60 的包（见 reports/baseline-report.md）：先修判分泄露面再扩题；")
    lines.append("- 实证 p=100 的题族（difficulty-emp-crosstab.md d1 列）：候选削题或加 hard 变体。")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written: {OUT}（{len(rows)} 包；低余量 {len(low)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

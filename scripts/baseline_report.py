# -*- coding: utf-8 -*-
"""基线分布报告（c242）：读 run 的 summary.baselines 块，输出 per-task
random/rules 分布 + 「接近满分」警告到 reports/baseline-report.md。

R17 事故类（a_irac rules 基线 96 分高于真实考生）的常驻化监控：rules/random
接近 100 的包是「判分可被无知识策略满足」的泄题前兆，发布前必须逐项归因。

用法：python scripts/baseline_report.py --run reports/runs/baseline-v06 [--warn 90]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "reports" / "baseline-report.md"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default=str(REPO / "reports" / "runs" / "baseline-v06"))
    ap.add_argument("--warn", type=float, default=90.0,
                    help="rules/random 任一包分值≥该阈值即列警告（缺省 90）")
    args = ap.parse_args()

    summary = json.loads((Path(args.run) / "summary.json")
                         .read_text(encoding="utf-8"))
    baselines = summary.get("baselines") or {}
    if not baselines:
        print(f"{args.run}: summary 无 baselines 块（mock run 无基线）")
        return 1

    warns: list[str] = []
    lines = [
        f"# 基线分布报告（{args.run}，阈值 ≥{args.warn:g} 警告）",
        "",
        "| 基线 | 任务包 | 分 |",
        "|---|---|---|",
    ]
    for kind in sorted(baselines):
        per_task = baselines[kind].get("per_task") or {}
        for tid in sorted(per_task, key=lambda t: -float(per_task[t])):
            v = float(per_task[tid])
            lines.append(f"| {kind} | {tid} | {v:.2f} |")
            if v >= args.warn:
                warns.append(f"{kind}/{tid} = {v:.2f}")

    lines += ["", "## 警告（接近满分 = 判分可被无知识策略满足，须逐项归因）", ""]
    if warns:
        lines += [f"- ⚠ {w}" for w in warns]
    else:
        lines.append(f"- 无：全部基线分 < {args.warn:g}")
    lines += ["",
              "归因口径（R7 c161）：rules 恒答 ok 对 expect=ok 题恒满是结构性非泄题；",
              "random 单题满分是确定性词汇抽取运气。判分锚引用（law_anchors）",
              "不得进基线可见面（R17）。"]

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written: {OUT}（警告 {len(warns)} 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

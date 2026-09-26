# -*- coding: utf-8 -*-
"""ledger ↔ summary.json 对账（round-23，c447；O4）。

`docs/run-score-ledger.md` 自称「唯一汇总账」但为手工登记；本脚本把 §1
主记分板各行的 grand_eq 与对应 run 产物的 `capability.grand_eq` 逐一比对，
**只报差异不改数字**——账面修正仍由人工按 run-score-ledger 记账纪律执行。

用法::

    python scripts/reconcile_ledger.py                  # 报告模式（恒 0 退出）
    python scripts/reconcile_ledger.py --strict         # 有差异/缺 summary → 退出 1
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEDGER = REPO / "docs" / "run-score-ledger.md"
RUNS = REPO / "reports" / "runs"

# 与 scripts/gen_panel_models.py 同一行正则（账本 §1 表行 → run/grand_eq）
LEDGER_ROW = re.compile(
    r"^\| \d+ \| `([a-z0-9\-]+)` \| ([^|]+?)（([^（）（）]+)） \| "
    r"(洁净隔离|API 隔离) \| \*{0,2}(\d+\.\d{2})\*{0,2} \|", re.M)


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    ledger = LEDGER
    if "--ledger" in argv:
        ledger = Path(argv[argv.index("--ledger") + 1])
    runs_root = RUNS
    if "--runs-root" in argv:
        runs_root = Path(argv[argv.index("--runs-root") + 1])
    text = ledger.read_text(encoding="utf-8")
    body = text.split("## 1. 主记分板", 1)[1].split("## 2.", 1)[0] \
        if "## 1. 主记分板" in text else text

    rows = LEDGER_ROW.findall(body)
    if not rows:
        print("RECONCILE: 账本 §1 未解析到任何行（格式漂移？）")
        return 1

    diffs: list[str] = []
    missing: list[str] = []
    for run, _name, _think, _purity, ledger_grand in rows:
        sp = runs_root / run / "summary.json"
        if not sp.is_file():
            missing.append(run)
            continue
        actual = json.loads(sp.read_text(encoding="utf-8")) \
            .get("capability", {}).get("grand_eq")
        if actual is None:
            diffs.append(f"{run}: summary 无 capability.grand_eq")
            continue
        if abs(float(actual) - float(ledger_grand)) > 0.005:
            diffs.append(f"{run}: 账面 {ledger_grand} ≠ 产物 {float(actual):.2f}")

    print(f"RECONCILE: 账面 {len(rows)} 行；缺 summary {len(missing)}；数字差异 {len(diffs)}")
    for d in diffs:
        print(f"  DIFF {d}")
    for m in missing:
        print(f"  MISSING {m}（reports/runs 为本地产，缺席须注明数据截至）")
    if strict and (diffs or missing):
        return 1
    print("RECONCILE: OK" if not diffs and not missing else "RECONCILE: 差异已列示（仅报告，不改账）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

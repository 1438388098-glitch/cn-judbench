# -*- coding: utf-8 -*-
"""capability 覆盖矩阵：12 任务包 × 8 能力维（主维计数）→ markdown。

按主 capability（capabilities.parse_capability 首维）计数，供论文
「能力维覆盖」表直接引用；Cit 属交叉维（crosscutting），不单列主维。
用法：python scripts/capability_matrix.py（无参数，写 reports/capability-matrix.md）
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cnjudbench.capabilities import (  # noqa: E402
    CANONICAL_DIMS, CROSSCUTTING, parse_capability,
)

DIMS = list(CANONICAL_DIMS) + list(CROSSCUTTING)
OUT = REPO / "reports" / "capability-matrix.md"


def main() -> int:
    rows: list[tuple[str, int, Counter]] = []
    for f in sorted((REPO / "data" / "public").glob("*.jsonl")):
        counts: Counter = Counter()
        n = 0
        for ln in f.read_text(encoding="utf-8-sig").splitlines():
            if not ln.strip():
                continue
            d = json.loads(ln)
            n += 1
            counts[parse_capability(d.get("capability"))[0]] += 1
        rows.append((f.stem, n, counts))

    total = sum(n for _, n, _ in rows)
    lines = [
        "# 能力维覆盖矩阵（12 包 × 8+1 维，按主维计数）",
        "",
        "主 capability 取 `capabilities.parse_capability` 首维；Cit 是横切红线维"
        "（FRAMEWORK §3.1），cit_validity 包以其为主分，单独成列。",
        "",
        "| 任务包 | n | " + " | ".join(f"{d}（{CANONICAL_DIMS.get(d) or CROSSCUTTING[d]}）" for d in DIMS) + " |",
        "|---|---|" + "---|" * len(DIMS),
    ]
    grand: Counter = Counter()
    for stem, n, counts in rows:
        grand.update(counts)
        lines.append(
            f"| {stem} | {n} | "
            + " | ".join(str(counts.get(d, 0)) for d in DIMS) + " |")
    lines.append(
        f"| **合计（主维）** | {total} | "
        + " | ".join(f"**{grand.get(d, 0)}**" for d in DIMS) + " |")
    empty = [d for d in DIMS if not grand.get(d)]
    if empty:
        lines.append(f"\n⚠ 零覆盖主维：{', '.join(empty)}（需在扩题计划中补齐）")
    else:
        lines.append("\n8+1 个维全部非零覆盖。")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written: {OUT}（{total} 题，{len(rows)} 包）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

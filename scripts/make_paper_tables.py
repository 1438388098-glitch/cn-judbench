# -*- coding: utf-8 -*-
"""论文主表生成（DESIGN v0.4 §6.1 模板 / §9）。

扫描 runs（默认 reports/runs/*），读各 run 的 summary.json，输出 Markdown 表：
- **T-main**（正式对比表）：只收 provisional=false 的 run（§8 门禁）；
- **T-provisional**（附录）：provisional=true 的 run 全量列出并显著标注。
用法::

    python scripts/make_paper_tables.py --runs reports/runs --out docs/paper-tables.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

COLUMNS = ["模型", "rev", "cap±CI", "hard±CI", "safety", "solve%",
           "$/solve", "pass_k", "flip%", "baselines", "provisional"]


def _row_from_summary(summary: dict) -> dict:
    ci = (summary.get("capability") or {})
    hard = ci.get("hard", "n/a")
    hc = ci.get("hard_ci95")
    hard_str = f"{hard} [{hc[0]},{hc[1]}]" if hc else str(hard)
    b = summary.get("baselines") or {}
    b_str = ("random=" + str((b.get("random") or {}).get("grand_eq", "n/a"))
             + " / rules=" + str((b.get("rules") or {}).get("grand_eq", "n/a")))
    solve = solved = 0
    for task in (summary.get("tasks") or {}).values():
        for it in task.get("items", []):
            if it.get("role") == "safety" or it.get("score") in (None, "n/a"):
                continue
            solve += 1
            solved += 1 if float(it["score"]) >= 60.0 else 0
    return {
        "模型": summary.get("model_id", "n/a"),
        "rev": str(summary.get("run_id", "n/a")),
        "cap±CI": str(ci.get("grand_eq", "n/a")),
        "hard±CI": hard_str,
        "safety": str(summary.get("safety_score", "n/a")),
        "solve%": f"{100.0 * solved / solve:.2f}" if solve else "n/a",
        "$/solve": str((summary.get("cost") or {}).get("dollar_per_solve") or "n/a"),
        "pass_k": str((summary.get("cost") or {}).get("pass_k") or "n/a"),
        "flip%": "n/a",  # flip 来自复跑脚本，summary 不携带（禁编造）
        "baselines": b_str,
        "provisional": str(summary.get("provisional", True)),
    }


def _md_table(rows: list[dict]) -> str:
    head = "| " + " | ".join(COLUMNS) + " |"
    sep = "|" + "|".join("---" for _ in COLUMNS) + "|"
    lines = [head, sep]
    lines += ["| " + " | ".join(r.get(c, "n/a") for c in COLUMNS) + " |" for r in rows]
    return "\n".join(lines)


def build_tables(runs_root: Path) -> tuple[str, int, int]:
    main_rows, prov_rows = [], []
    for d in sorted(runs_root.iterdir()) if runs_root.is_dir() else []:
        sp = d / "summary.json"
        if not sp.is_file():
            continue
        try:
            s = json.loads(sp.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        row = _row_from_summary(s)
        (prov_rows if s.get("provisional", True) else main_rows).append(row)
    parts = [f"# 论文主表（生成自 {runs_root}，正式对比表只收 provisional=false）\n"]
    parts.append("## T-main（正式对比表）\n")
    parts.append(_md_table(main_rows) if main_rows else "（暂无——缺 deps 锁或 flip 复跑的 run 均为 provisional，见附录）\n")
    parts.append("\n## T-provisional（附录；provisional=true 不得进 T-main）\n")
    parts.append(_md_table(prov_rows) if prov_rows else "（无 provisional run）\n")
    return "\n".join(parts), len(main_rows), len(prov_rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="reports/runs")
    ap.add_argument("--out", default=None, help="缺省打印 stdout")
    args = ap.parse_args()
    text, n_main, n_prov = build_tables(Path(args.runs))
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    print(f"rows: main={n_main} provisional={n_prov}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

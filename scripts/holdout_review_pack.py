# -*- coding: utf-8 -*-
"""holdout 双审材料包生成（协议 §4 前置；不执行 --apply）。

用 freeze_holdout.pick_ids 的确定性抽样生成「拟冻结名单」，连同种子、
逐包统计、双人复核核对清单写入：
- reports/holdout-prospective.json  （机器可读：逐包入选 id + item_line_hash）
- docs/holdout-dual-review-pack.md  （人读：复核清单 + 签字栏）

双人复核（协议 §4）：两位复核人独立核对本包名单的分层比例与种子复算，
均签字后方可执行 freeze_holdout.py --apply。本脚本只读，不修改 data/。
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

from freeze_holdout import PUBLIC, RATIO, SEED_PREFIX, pick_ids  # noqa: E402


def item_line_hash(item_id: str, raw_line: str) -> str:
    blob = f"{item_id}\n{raw_line}".encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def main() -> int:
    pack: dict = {
        "note": "holdout 拟冻结名单（未执行 --apply）；种子=sha256(cnjb-holdout-v1:<task>)[:8]",
        "seed_prefix": SEED_PREFIX,
        "ratio": RATIO,
        "generated": date.today().isoformat(),
        "packages": {},
    }
    lines_md = [
        "# holdout 冻结双人复核材料包",
        "",
        f"> 生成日期：{date.today().isoformat()} · 抽样比例 {RATIO:.0%} · "
        f"种子前缀 `{SEED_PREFIX}<task_id>`（sha256 前 8 hex，任何人可复算）",
        "",
        "## 复核清单（每位复核人独立完成后签字）",
        "",
        "1. 逐包核对入选题数 = max(3, ceil(n×0.30))，与下表一致；",
        "2. 复算任选 2 包的种子与抽样序列（改动任一题的 id 集应可发现）；",
        "3. 抽查 5 题确认 hard（difficulty≥3）保比例逻辑；",
        "4. 确认 data/public 对应行删除后 `cnjudbench validate` 与 pytest 全绿；",
        "5. 双人签字后，由执行人运行 `python scripts/freeze_holdout.py --apply` 并归档本文件。",
        "",
        "| 任务包 | 包内题数 | 拟冻结 | hard 占比 |",
        "|---|---|---|---|",
    ]
    total = 0
    for src in sorted(PUBLIC.glob("*.jsonl")):
        task_id = src.stem
        rows = [json.loads(l) for l in src.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
        chosen = pick_ids(task_id, rows)
        chosen_set = set(chosen)
        hard_all = sum(1 for r in rows if r.get("difficulty", 0) >= 3)
        hard_pick = sum(1 for r in rows if r.get("difficulty", 0) >= 3 and r["id"] in chosen_set)
        hashes = {r["id"]: item_line_hash(r["id"], l.strip())
                  for r, l in zip(rows, src.read_text(encoding="utf-8-sig").splitlines())
                  if l.strip() and r["id"] in chosen_set}
        pack["packages"][task_id] = {
            "n_total": len(rows), "n_chosen": len(chosen),
            "n_hard_total": hard_all, "n_hard_chosen": hard_pick,
            "seed": hashlib.sha256((SEED_PREFIX + task_id).encode()).hexdigest()[:8],
            "ids": chosen, "item_line_hashes": hashes,
        }
        lines_md.append(f"| {task_id} | {len(rows)} | {len(chosen)} "
                        f"({hard_pick}/{len(chosen)} hard) | {hard_all}/{len(rows)} |")
        total += len(chosen)

    lines_md += ["", f"**合计拟冻结 {total} 题。**", "",
                 "## 签字栏", "",
                 "- 复核人 A：____________ 日期：________",
                 "- 复核人 B：____________ 日期：________",
                 "- 执行人（--apply 后回填 commit/manifest）：____________", ""]
    out_json = REPO / "reports" / "holdout-prospective.json"
    out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    (REPO / "docs" / "holdout-dual-review-pack.md").write_text("\n".join(lines_md), encoding="utf-8")
    print(f"written: {out_json}")
    print(f"written: {REPO / 'docs' / 'holdout-dual-review-pack.md'}")
    print(f"prospective freeze total: {total} items (dry; data untouched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

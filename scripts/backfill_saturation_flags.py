# -*- coding: utf-8 -*-
"""回填饱和题标注（v0.6：difficulty-audit-v05 T4a/T4b → saturation_flag=true）。

数据源：reports/difficulty-audit-v05.json（双考生/三样本实测逐题 tier）。
只标注 **public** 里的题（archive 已移出发布口径）；T4b 是「待第 3 样本」，
同样先标 true 并在 dataset-card 注明口径——发布统计建议剔除或单列，
正主分口径不变（剔除与否由报表消费者决定，金样不动）。

用法：python scripts/backfill_saturation_flags.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO / "reports" / "difficulty-audit-v05.json"
PUBLIC = REPO / "data" / "public"


def main() -> int:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    flagged: dict[str, dict] = {}
    for key, v in audit.items():
        if str(v.get("tier", "")).startswith("T4"):
            task_id, item_id = key.split("/", 1)
            flagged.setdefault(task_id, {})[item_id] = v["tier"]

    total = 0
    for src in sorted(PUBLIC.glob("*.jsonl")):
        task_id = src.stem
        want = flagged.get(task_id)
        if not want:
            continue
        rows = [json.loads(l) for l in src.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
        changed = False
        for r in rows:
            if r["id"] in want and r.get("saturation_flag") is not True:
                r["saturation_flag"] = True
                changed = True
                total += 1
        if changed:
            src.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                encoding="utf-8")
    print(f"saturation_flag=true backfilled: {total} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())

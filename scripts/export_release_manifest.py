# -*- coding: utf-8 -*-
"""发布态数据 MANIFEST 生成（v0.6 污染防控发布设施）。

逐题产出 item_line_hash（与 run manifest 同函数，可互核）+ canary + 题面字节数，
连同 lawkb VERSION 与数据集级汇总 hash 写入 ``data/public/MANIFEST.json``。

用途：第三方拿到数据集后可检测「这道题是否在某时点已存在」——污染分级的
最低配公开基础设施（dataset-card §4 对应承诺）。数据或题面任何一字改动都会
改变对应条目 hash。

用法：python scripts/export_release_manifest.py   （数据变更后重跑并提交）
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cnjudbench.lawkb.store import LawkbStore  # noqa: E402
from cnjudbench.runner.manifest import item_line_hash  # noqa: E402

PUBLIC = REPO / "data" / "public"


def main() -> int:
    store = LawkbStore.load(REPO / "lawkb")
    packages: dict[str, dict] = {}
    all_hashes: list[str] = []
    for src in sorted(PUBLIC.glob("*.jsonl")):
        task_id = src.stem
        items: dict[str, dict] = {}
        raw_lines = src.read_text(encoding="utf-8-sig").splitlines()
        for line in raw_lines:
            if not line.strip():
                continue
            row = json.loads(line)
            h = item_line_hash(row["id"], line.strip())
            items[row["id"]] = {
                "item_line_hash": h,
                "canary": row.get("canary"),
                "difficulty": row.get("difficulty"),
                "saturation_flag": bool(row.get("saturation_flag", False)),  # c150
                "bytes": len(line.strip().encode("utf-8")),
            }
            all_hashes.append(h)
        packages[task_id] = {"n_items": len(items), "items": items}

    blob = "".join(sorted(all_hashes)).encode("utf-8")
    manifest = {
        "note": ("CN-JudBench public split 发布清单：逐题 item_line_hash 与 run manifest "
                 "同源（runner.manifest.item_line_hash），任何题面改动可被第三方检测。"),
        "generated": date.today().isoformat(),
        "lawkb_store_version": store.store_version,
        "dataset_content_hash": "sha256:" + hashlib.sha256(blob).hexdigest(),
        "n_items_total": sum(p["n_items"] for p in packages.values()),
        "packages": packages,
    }
    out = PUBLIC / "MANIFEST.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"written: {out}")
    print(f"items={manifest['n_items_total']} dataset_content_hash={manifest['dataset_content_hash']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

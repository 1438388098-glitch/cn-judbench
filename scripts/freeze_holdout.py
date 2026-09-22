# -*- coding: utf-8 -*-
"""holdout 冻结工具（docs/holdout-live-protocol.md §2）。

分层保比例抽样：种子 = sha256("cnjb-holdout-v1:" + task_id)[:8]，任何人可复算。
默认 dry-run 只打印名单；--apply 物理移动题到 data/holdout/ 并从 data/public 移除。
⚠️ --apply 是发布动作，执行前须双人复核（协议 §4）。
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"
HOLDOUT = ROOT / "data" / "holdout"
RATIO = 0.30
MIN_PER_TASK = 3
SEED_PREFIX = "cnjb-holdout-v1:"


def pick_ids(task_id: str, items: list[dict]) -> list[str]:
    """分层抽样：hard（difficulty≥3）按包内占比保比例；种子确定性。"""
    seed = int(hashlib.sha256((SEED_PREFIX + task_id).encode()).hexdigest()[:8], 16)
    n_total = max(MIN_PER_TASK, int(len(items) * RATIO + 0.999))
    hard = [it for it in items if it.get("difficulty", 0) >= 3]
    easy = [it for it in items if it.get("difficulty", 0) < 3]
    n_hard = round(n_total * len(hard) / len(items)) if items else 0
    n_hard = min(max(n_hard, 0), len(hard))
    rng = random.Random(seed)
    picked = sorted(hard, key=lambda x: x["id"])
    rng.shuffle(picked)
    out = [x["id"] for x in picked[:n_hard]]
    rest = sorted(easy, key=lambda x: x["id"])
    rng.shuffle(rest)
    out += [x["id"] for x in rest[: n_total - len(out)]]
    return sorted(out)


def freeze_task(task_id: str, apply: bool) -> tuple[str, int]:
    src = PUBLIC / f"{task_id}.jsonl"
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    chosen = set(pick_ids(task_id, rows))
    if not apply:
        print(f"[dry-run] {task_id}: {len(chosen)}/{len(rows)} -> {sorted(chosen)}")
        return task_id, len(chosen)
    HOLDOUT.mkdir(parents=True, exist_ok=True)
    keep, move = [], []
    for r in rows:
        (move if r["id"] in chosen else keep).append(r)
    for r in move:
        r["split"] = "holdout"
    (PUBLIC / f"{task_id}.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in keep) + "\n", encoding="utf-8")
    (HOLDOUT / f"{task_id}.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in move) + "\n", encoding="utf-8")
    print(f"[applied] {task_id}: moved {len(move)}, public keeps {len(keep)}")
    return task_id, len(move)


def main() -> int:
    apply = "--apply" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    task_ids = only or sorted(p.stem.replace(".jsonl", "") for p in PUBLIC.glob("*.jsonl"))
    total = 0
    for tid in task_ids:
        _, n = freeze_task(tid, apply)
        total += n
    print(f"{'applied' if apply else 'dry-run'}: {total} 题" if apply
          else f"dry-run: 共 {total} 题入选（未动数据）")
    if apply:
        print("注意：数据量相关测试断言需同步更新（协议 §4）；data/holdout/ 已入 .gitignore。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

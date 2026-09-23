# -*- coding: utf-8 -*-
"""holdout 冻结协议（docs/holdout-live-protocol.md §2）：确定性分层抽样。"""

from __future__ import annotations

import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from freeze_holdout import pick_ids  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _load(task: str) -> list[dict]:
    return [json.loads(l) for l in
            (REPO / "data" / "public" / f"{task}.jsonl")
            .read_text(encoding="utf-8-sig").splitlines() if l.strip()]


def test_pick_ids_deterministic_and_ratio():
    items = _load("u_element_extract")
    a = pick_ids("u_element_extract", items)
    b = pick_ids("u_element_extract", items)
    assert a == b  # 预注册名单：任何人复算同一份
    assert len(a) == 15  # ceil(49*0.3)（v0.5 Phase 3c 后 u_element 49 题）
    # hard（difficulty≥3，包内 34 题，占比 ~69%）分层保比例：入选 hard 数应接近占比
    hard_picked = sum(1 for i in a if next(x for x in items if x["id"] == i)
                      .get("difficulty", 0) >= 3)
    assert hard_picked >= 5  # 15×0.69≈10.4，容忍抽样波动但不得塌成全 easy


def test_pick_ids_min_per_task():
    tiny = [{"id": f"x-{i}", "difficulty": i % 2 + 1} for i in range(4)]
    assert len(pick_ids("some-tiny-task", tiny)) == 3  # MIN_PER_TASK

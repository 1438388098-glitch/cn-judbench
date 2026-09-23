# -*- coding: utf-8 -*-
"""R38：应拒题考生须知必须覆盖判分口径（refuse 协议进题面）。"""

from __future__ import annotations

from pathlib import Path

from cnjudbench.runner.evaluate import _build_prompt, load_task_package
from cnjudbench.schemas.item import Item

REPO = Path(__file__).resolve().parents[1]


def _item(item_id: str, path: str) -> Item:
    for line in (REPO / path).read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            d = json.loads(line) if (json := __import__("json")) else None
            if d["id"] == item_id:
                return Item.model_validate(d)
    raise AssertionError(item_id)


def test_refuse_items_render_refuse_protocol():
    task, _ = load_task_package(REPO / "tasks" / "a_irac_reason")
    p = _build_prompt(task, _item("a-021", "data/public/a_irac_reason.jsonl"))
    assert '"expect": "refuse"' in p and "advice" in p
    assert '"issue"' not in p  # 不得再暴露 IRAC schema 误导考生

def test_regular_items_keep_task_template():
    task, _ = load_task_package(REPO / "tasks" / "a_irac_reason")
    p = _build_prompt(task, _item("a-015", "data/public/a_irac_reason.jsonl"))
    assert '"issue"' in p and "IRAC" in p

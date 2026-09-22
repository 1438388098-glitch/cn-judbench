# -*- coding: utf-8 -*-
"""R46：refuse 协议一致性公平性规则（E16 教训固化，candidate-062）。"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from cnjudbench.schemas.task import TaskManifest
from cnjudbench.validate.items import validate_items_file

REPO = Path(__file__).resolve().parents[1]


def _validate_one(mutate) -> list[str]:
    tasks = {"a_irac_reason": TaskManifest.model_validate(
        __import__("yaml").safe_load(
            (REPO / "tasks" / "a_irac_reason" / "task.yaml").read_text(encoding="utf-8-sig")))}
    rows = [json.loads(l) for l in
            (REPO / "data" / "public" / "a_irac_reason.jsonl").read_text(encoding="utf-8-sig").splitlines()
            if l.strip()]
    it = next(r for r in rows if r["id"] == "a-020")
    mutate(it)
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        p = Path(f.name)
    try:
        return validate_items_file(p, tasks)
    finally:
        p.unlink()


def test_refuse_predicates_without_goal_flagged():
    def drop_goal(it):
        it["state_goal"] = None
    errs = [e for e in _validate_one(drop_goal) if "a-020" in e and "公平性" in e]
    assert errs, "refuse 判分文件但无 state_goal.expect 应报公平性错误"


def test_goal_without_refuse_predicates_flagged():
    def swap_ref(it):
        it["predicates_ref"] = "tasks/a_irac_reason/predicates.yaml"
    errs = [e for e in _validate_one(swap_ref) if "a-020" in e and "公平性" in e]
    assert errs, "expect=refuse 但常规判分文件应报公平性错误"

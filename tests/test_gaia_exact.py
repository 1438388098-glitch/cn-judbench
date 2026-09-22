"""P2：Legal-GAIA L3a exact 主分 + progress 诊断列（impl-P2 §4/§8 test_gaia_exact）。"""

from __future__ import annotations

import json
from pathlib import Path

from cnjudbench.adapters.mock import MockAdapter
from cnjudbench.runner.evaluate import evaluate_item, load_task_package
from cnjudbench.validate.items import load_items_file

REPO = Path(__file__).resolve().parents[1]
TASK_DIR = REPO / "tasks" / "gaia_fee_deadline"


def _items() -> list:
    return [it for _ln, it in
            load_items_file(REPO / "data" / "public" / "gaia_fee_deadline.jsonl")]


def _eval(item, answer_obj: dict, store):
    task, default_preds = load_task_package(TASK_DIR)
    import yaml
    from cnjudbench.schemas.task import PredicatesFile

    preds = default_preds
    if item.predicates_ref:
        preds = PredicatesFile.model_validate(
            yaml.safe_load((REPO / item.predicates_ref).read_text(encoding="utf-8"))
        )
    return evaluate_item(task, preds, item,
                         MockAdapter(lambda _p: json.dumps(answer_obj, ensure_ascii=False)), store)


def test_ten_items_exact_gold_full_score(store):
    """10 题精品：mock:gold 终答 → 全 100.00（gold 不进 prompt）。"""
    items = _items()
    assert len(items) == 12
    for item in items:
        answer_obj = {"answer": item.gold["answer"], "steps": item.gold["steps"]}
        r = _eval(item, answer_obj, store)
        assert r.display == "100.00", (item.id, r.display, r.error, r.predicate_lines)


def test_wrong_answer_is_zero_not_partial(store):
    """exact 语义：错终答 → 0.00（on_fail zero），即使步骤齐全。"""
    item = next(it for it in _items() if it.id == "g-01")
    r = _eval(item, {"answer": "5000", "steps": item.gold["steps"]}, store)
    assert r.display == "0.00"


def test_progress_is_diagnostic_only(store):
    """progress 单独可算：steps 缺失 → progress FAIL，但主分不受影响。"""
    item = next(it for it in _items() if it.id == "g-01")
    r = _eval(item, {"answer": "5050", "steps": []}, store)
    assert r.display == "100.00"  # 主分不动
    assert r.diag_score is not None and r.diag_score < 100.0  # 诊断列下降
    assert any("progress_keyword" in line for line in r.predicate_lines)


def test_dual_as_of_item_exists(store):
    """双 as_of 题面（g-06）金样为两状态拼接。"""
    item = next(it for it in _items() if it.id == "g-06")
    assert item.gold["answer"] == "not_yet_effective;ok"

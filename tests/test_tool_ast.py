"""P2：工具序列与参数 AST 谓词（impl-P2 §3/§8 test_tool_ast）。"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from cnjudbench.adapters.mock import MockAdapter
from cnjudbench.runner.evaluate import evaluate_item, load_task_package
from cnjudbench.schemas.task import PredicatesFile
from cnjudbench.validate.items import load_items_file

REPO = Path(__file__).resolve().parents[1]
TASK_DIR = REPO / "tasks" / "tool_search_statute"


def _eval(item_id: str, payload: dict, store):
    """按题 predicates_ref 构造谓词集后判分（与 run_task 同口径）。"""
    task, default_preds = load_task_package(TASK_DIR)
    for _lineno, item in load_items_file(REPO / "data" / "public" / "tool_search_statute.jsonl"):
        if item.id == item_id:
            preds = default_preds
            if item.predicates_ref:
                preds = PredicatesFile.model_validate(
                    yaml.safe_load((REPO / item.predicates_ref).read_text(encoding="utf-8"))
                )
            return evaluate_item(task, preds, item,
                                 MockAdapter(lambda _p: json.dumps(payload, ensure_ascii=False)),
                                 store)
    raise KeyError(item_id)


def test_wrong_args_partial_score(store):
    """参数错型 → tool_ast 比例 1/2 → 题分 = 100 × 1.0 × 0.5 = 50.00。"""
    payload = {"calls": [
        {"name": "calc_fee", "args": {"amount": "八千", "type": "财产案件"}},  # 错型
        {"name": "calc_fee", "args": {"amount": 8000, "type": "财产案件"}},   # 正确
    ], "answer": {"fee": 50}}
    r = _eval("t-cf-001", payload, store)
    assert r.display == "50.00"
    assert any("tool_ast" in line and "FAIL" in line for line in r.predicate_lines)
    assert "tool_arg_invalid" in r.taxonomy


def test_missing_expected_tool_partial(store):
    """漏调（序列覆盖 0）→ seq × ast 全灭 → 0.00（partial 乘法）。"""
    payload = {"calls": [{"name": "search_statute", "args": {"query": "诉讼费", "as_of": "2024-06-01"}}],
               "answer": {"fee": 50}}
    r = _eval("t-cf-001", payload, store)
    assert r.display == "0.00"
    assert any("tool_sequence" in line and "FAIL" in line for line in r.predicate_lines)
    assert "tool_miss" in r.taxonomy


def test_correct_calls_full_score(store):
    good = {"calls": [{"name": "calc_fee", "args": {"amount": 8000, "type": "财产案件"}}],
            "answer": {"fee": 50}}
    r = _eval("t-cf-001", good, store)
    assert r.display == "100.00"
    assert r.trajectory is not None
    assert r.trajectory["calls"][0]["ok"] is True

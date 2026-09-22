"""P2：假调用检测（impl-P2 §5/§8 test_fake_tool / DoD 3 假调用夹具必现 0.00）。"""

from __future__ import annotations

import json
from pathlib import Path

from cnjudbench.adapters.mock import MockAdapter
from cnjudbench.runner.evaluate import evaluate_item, load_task_package
from cnjudbench.schemas.item import Item
from cnjudbench.validate.items import load_items_file

REPO = Path(__file__).resolve().parents[1]
TASK_DIR = REPO / "tasks" / "tool_search_statute"


def _pkg():
    return load_task_package(TASK_DIR)


def _item(item_id: str) -> Item:
    path = REPO / "data" / "public" / "tool_search_statute.jsonl"
    for _lineno, item in load_items_file(path):
        if item.id == item_id:
            return item
    raise KeyError(item_id)


def _eval(item: Item, text: str, store):
    task, _ = _pkg()
    return evaluate_item(task, load_task_package(TASK_DIR)[1], item,
                         MockAdapter(lambda _p: text), store)


def test_negative_fixture_fake_tool_zero(store):
    """t-fake-001：只叙述不调用 → 0.00 + fake_tool（负例夹具）。"""
    r = _eval(_item("t-fake-001"), "我已检索了相关法律，本案受理费为 50 元。", store)
    assert r.display == "0.00"
    assert "fake_tool" in r.taxonomy


def test_unregistered_tool_call_zero(store):
    """调了未注册工具（web_search）→ fake_tool 0.00，即使终答碰巧正确。"""
    bad = {"calls": [{"name": "web_search", "args": {"query": "诉讼费 8000"}}],
           "answer": {"fee": 50}}
    r = _eval(_item("t-cf-001"), json.dumps(bad, ensure_ascii=False), store)
    assert r.display == "0.00"
    assert "fake_tool" in r.taxonomy


def test_silent_no_call_expected_zero(store):
    """期望调用但完全没调用（连叙述都没有）→ fake_tool 0.00。"""
    silent = {"calls": [], "answer": {"fee": 50}}
    r = _eval(_item("t-cf-001"), json.dumps(silent, ensure_ascii=False), store)
    assert r.display == "0.00"
    assert "fake_tool" in r.taxonomy


def test_non_tool_task_parse_fail_stays_format_fail(store):
    """L1 structured 任务解析失败仍是 format_fail（不扩大 fake_tool 适用面）。"""
    task, preds = load_task_package(REPO / "tasks" / "cit_validity")
    item = next(it for _ln, it in load_items_file(REPO / "data" / "public" / "cit_validity.jsonl"))
    r = evaluate_item(task, preds, item, MockAdapter(lambda _p: "这不是 JSON"), store)
    assert r.display == "0.00" and "format_fail" in r.taxonomy

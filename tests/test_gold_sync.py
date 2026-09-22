"""gold 三源同源：题面 gold ↔ 沙箱重放 result（防实现改费率而题面 gold 未同步）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.tools import ToolSandbox
from cnjudbench.validate.items import load_items_file

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def store():
    return LawkbStore.load(ROOT / "lawkb")


@pytest.fixture(scope="module")
def sandbox(store):
    return ToolSandbox(store)


def test_tool_item_gold_matches_sandbox(store, sandbox):
    path = ROOT / "data" / "public" / "tool_search_statute.jsonl"
    items = [it for _ln, it in load_items_file(path) if it.output_type == "tool_call"]
    assert items, "tool_search_statute 题面为空"
    mismatches: list[str] = []
    for item in items:
        gold = item.gold if isinstance(item.gold, dict) else {}
        if gold.get("negative") == "fake_tool":
            continue
        calls = gold.get("calls") or []
        answer = gold.get("answer") or {}
        results = []
        for c in calls:
            if not isinstance(c, dict):
                continue
            sb = ToolSandbox(store)
            entry = sb.execute(str(c.get("name") or ""), c.get("args"))
            if not entry.ok:
                mismatches.append(f"{item.id}: call fail {c} -> {entry.error}")
                continue
            results.append((str(c.get("name")), entry.result))
        if not results:
            continue
        last = results[-1][1]
        if not isinstance(last, dict):
            continue
        if "fee" in answer and last.get("fee") is not None and last["fee"] != answer["fee"]:
            mismatches.append(f"{item.id}: fee gold={answer['fee']} sandbox={last['fee']}")
        if "date" in answer and last.get("deadline") is not None and last["deadline"] != answer["date"]:
            mismatches.append(f"{item.id}: date gold={answer['date']} sandbox={last['deadline']}")
        if "status" in answer and last.get("status") is not None and last["status"] != answer["status"]:
            mismatches.append(f"{item.id}: status gold={answer['status']} sandbox={last['status']}")
    assert not mismatches, "\n".join(mismatches)


def test_gaia_fee_answer_matches_sandbox(store):
    """gaia 金额题终答须与沙箱 calc_fee 同源（5050/12800/300）。"""
    path = ROOT / "data" / "public" / "gaia_fee_deadline.jsonl"
    items = [it for _ln, it in load_items_file(path)]
    by_id = {it.id: it for it in items}
    sb = ToolSandbox(store)
    for item_id, args, expect in [
        ("g-01", {"amount": 250000, "type": "财产案件"}, 5050),
        ("g-08", {"amount": 900000, "type": "财产案件"}, 12800),
        ("g-05", {"amount": 12000, "type": "离婚案件"}, 300),
    ]:
        item = by_id[item_id]
        entry = sb.execute("calc_fee", args)
        assert entry.ok, (item_id, entry.error)
        assert entry.result["fee"] == expect
        assert str(item.gold["answer"]) == str(expect)

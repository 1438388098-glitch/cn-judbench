"""P3：终态 F1 金样。"""

from __future__ import annotations

from cnjudbench.dialog.state_score import state_f1


def test_state_f1_exact_match():
    goal = {"matter_type": "民间借贷", "risk_level": "high"}
    ans = {"matter_type": "民间借贷", "risk_level": "high"}
    r = state_f1(ans, goal)
    assert r["f1"] == 1.0
    assert r["missing"] == []


def test_state_f1_partial_scalar():
    goal = {"matter_type": "民间借贷", "risk_level": "high"}
    ans = {"matter_type": "民间借贷", "risk_level": "low"}
    r = state_f1(ans, goal)
    assert 0.4 <= r["f1"] <= 0.6
    assert "risk_level" in r["missing"]


def test_state_f1_list_overlap():
    goal = {"parties": ["张某", "李某"]}
    ans = {"parties": ["张某"]}
    r = state_f1(ans, goal)
    assert 0.5 <= r["f1"] < 1.0


def test_state_f1_empty_goal():
    assert state_f1({}, {})["f1"] == 1.0

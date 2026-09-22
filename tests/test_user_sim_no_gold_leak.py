"""P3：模拟用户禁止把 gold 字面塞进话术。"""

from __future__ import annotations

import json

import pytest

from cnjudbench.dialog.user_sim import UserSim, gold_literals
from cnjudbench.schemas.item import Item
from cnjudbench.schemas.user_script import UserScript


def _item() -> Item:
    return Item.model_validate(json.loads(r'''
    {"id": "tj-leak", "task_id": "tau_jud_intake", "capability": "C", "difficulty": 2,
     "interaction": "L3b", "roles": ["lawyer"], "domain": "civil_commercial",
     "output_type": "structured", "hcut": ["Proto"], "source": "synthetic",
     "instruction": "接待", "input": "借款纠纷",
     "gold": {"matter_type": "民间借贷"},
     "state_goal": {"matter_type": "民间借贷", "parties": ["张某"]},
     "law_anchors": [{"law": "中华人民共和国民法典", "article": "577"}],
     "as_of": "2024-06-01", "canary": "CNJB-CANARY-af01",
     "split": "public", "contamination_risk": "low"}
    '''))


def test_gold_literals_from_state_goal():
    lits = gold_literals(_item())
    assert "民间借贷" in lits
    assert "张某" in lits


def test_user_sim_rejects_leaking_script():
    script = UserScript.model_validate({
        "script_id": "bad",
        "personas": [{"id": "p1", "tone": "普通"}],
        "sampling": "fixed_order",
        "turns": ["请问民间借贷怎么办？"],
    })
    with pytest.raises(ValueError):
        UserSim(script, _item(), user_seed=1)


def test_user_sim_turns_do_not_leak_gold():
    script = UserScript.model_validate({
        "script_id": "ok",
        "personas": [{"id": "p-cooperative", "tone": "合作"}],
        "sampling": "seeded_sample",
        "turn_budget": 4,
        "turns": ["我需要评估风险。", "请给出下一步。"],
    })
    sim = UserSim(script, _item(), user_seed=42)
    for i in range(4):
        line = sim.next_turn(i, "ok")
        for lit in gold_literals(_item()):
            assert lit not in line

# -*- coding: utf-8 -*-
"""round-19（c441）：对话确定性直测——pick_persona 三采样策略与 dump_dialog
序列化契约。user_sim 种子确定性是 c400（crc32 修复）的承重面。
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _user_sim():
    from cnjudbench.dialog import user_sim
    return user_sim


def _script(sampling: str):
    from cnjudbench.schemas.user_script import Persona, UserScript

    return UserScript(
        script_id="s-test",
        personas=[
            Persona(id="p-anxious", tone="急"),
            Persona(id="p-vague", tone="含糊"),
            Persona(id="p-cooperative", tone="配合"),
        ],
        sampling=sampling,
    )


def test_pick_persona_fixed_order():
    mod = _user_sim()
    assert mod.pick_persona(_script("fixed_order"), 0).id == "p-anxious"
    assert mod.pick_persona(_script("fixed_order"), 999).id == "p-anxious"


def test_pick_persona_persona_cycle_is_seed_modulo():
    mod = _user_sim()
    s = _script("persona_cycle")
    assert mod.pick_persona(s, 0).id == "p-anxious"
    assert mod.pick_persona(s, 1).id == "p-vague"
    assert mod.pick_persona(s, 2).id == "p-cooperative"
    assert mod.pick_persona(s, 3).id == "p-anxious"  # 循环


def test_pick_persona_seeded_sample_is_deterministic():
    mod = _user_sim()
    s = _script("seeded_sample")
    a = mod.pick_persona(s, 42)
    b = mod.pick_persona(s, 42)
    assert a.id == b.id  # 同 seed 同人设（跨进程确定性，c400 纪律）
    ids = {mod.pick_persona(s, seed).id for seed in range(12)}
    assert len(ids) > 1  # 不同 seed 应能取到不同人设（不是退化成单点）


def test_dump_dialog_serializable_view():
    from cnjudbench.dialog import session as mod
    from cnjudbench.dialog.proto import ProtoResult

    result = mod.DialogResult(
        item_id="t-001",
        score=50.0,
        display="50.00",
        state_f1=0.5,
        proto=ProtoResult(passed={"risk_disclosure": True}, redline=[], notes={}),
        turns=[mod.DialogTurn(role="user", text="你好"), mod.DialogTurn(role="assistant", text="您好")],
        taxonomy=["partial_coverage"],
        user_seed=1,
        model_seed=2,
        n_turns=2,
    )
    d = mod.dump_dialog(result)
    assert d["item_id"] == "t-001" and d["score"] == "50.00"
    assert d["state_f1"] == 0.5 and len(d["turns"]) == 2
    json.dumps(d, ensure_ascii=False)  # 必须可直接序列化（写盘 + hash 前置）

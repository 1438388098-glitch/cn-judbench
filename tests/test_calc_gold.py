"""P2：calc_deadline / calc_fee 金样逐条锁定（impl-P2 §8 test_calc_gold / DoD 5）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.tools import ToolSandbox

GOLD = Path(__file__).resolve().parents[1] / "src" / "cnjudbench" / "tools" / "gold"


def _gold(name: str) -> list[dict]:
    return json.loads((GOLD / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sandbox(tmp_path_factory):
    # store 只为满足签名；deadline/fee 是纯函数，不触库
    store = LawkbStore.load(Path(__file__).resolve().parents[1] / "lawkb")
    return ToolSandbox(store)


def test_calc_deadline_gold(sandbox):
    cases = _gold("deadline.json")
    assert len(cases) >= 5
    for c in cases:
        entry = sandbox.execute("calc_deadline", c["args"])
        assert entry.ok, (c, entry.error)
        assert entry.result["deadline"] == c["expect"], c


def test_calc_deadline_weekend_roll_is_deterministic(sandbox):
    r1 = sandbox.execute("calc_deadline", {"start": "2024-05-31", "type": "民事上诉"})
    r2 = sandbox.execute("calc_deadline", {"start": "2024-05-31", "type": "民事上诉"})
    assert r1.result == r2.result
    assert r1.result["weekend_rolled"] is True


def test_calc_fee_gold(sandbox):
    cases = _gold("fee.json")
    assert len(cases) >= 5
    for c in cases:
        entry = sandbox.execute("calc_fee", c["args"])
        assert entry.ok, (c, entry.error)
        assert entry.result["fee"] == c["expect"]["fee"], c

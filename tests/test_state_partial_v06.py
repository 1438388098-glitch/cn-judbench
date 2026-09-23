"""v0.6 state 谓词部分得分改造：键均比例 + on_fail=partial 联动。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.predicates.base import EvalContext
from cnjudbench.predicates.ptp import state as state_pred
from cnjudbench.predicates.registry import compose_score
from cnjudbench.predicates.base import PredicateResult

REPO = Path(__file__).resolve().parents[1]


def _ctx(answer: dict, state_goal: dict) -> EvalContext:
    store = LawkbStore.load(REPO / "lawkb")
    item = SimpleNamespace(id="tj-000", state_goal=state_goal, gold={})
    return EvalContext(task=None, item=item, answer=answer, answer_text="", claims=[],
                       claim_status="ok", store=store, checks=[], tool_log=[])


class _P:
    """最小谓词桩：p.model_extra / p.on_fail。"""

    def __init__(self, on_fail="partial", expect=None):
        self.on_fail = on_fail
        self.model_extra = {"expect": expect} if expect else {}


def test_full_match_ratio_one_and_ok():
    goal = {"matter_type": "民间借贷", "risk_level": "high", "key_facts": ["借款十万元", "约定利息"]}
    ctx = _ctx({"matter_type": "民间借贷", "risk_level": "high",
                "key_facts": ["借款十万元", "约定利息"]}, goal)
    r = state_pred(ctx, _P(), 0)
    assert r.passed and r.pass_ratio == 1.0 and r.failure_taxonomy is None


def test_free_text_partial_credit():
    # risk_note 同义改写：不再全有全无，得重叠比例分
    goal = {"risk_note": "诉讼时效将于2024年6月18日届满，不能保证结果"}
    ctx = _ctx({"risk_note": "注意时效风险，建议尽快起诉，结局难料无法保证"}, goal)
    r = state_pred(ctx, _P(), 0)
    assert 0.0 < r.pass_ratio < 1.0
    assert not r.passed and r.failure_taxonomy == "state_drift"


def test_missing_key_zero_and_mixed_mean():
    goal = {"matter_type": "民间借贷", "risk_level": "high"}
    ctx = _ctx({"matter_type": "民间借贷"}, goal)  # risk_level 缺失
    r = state_pred(ctx, _P(), 0)
    assert abs(r.pass_ratio - 0.5) < 1e-9


def test_list_key_graded():
    goal = {"key_facts": ["借款十万元", "利息约定不明", "被告已还部分"]}
    ctx = _ctx({"key_facts": ["借款十万元"]}, goal)  # 3 项中 1 项命中
    r = state_pred(ctx, _P(), 0)
    assert 0.0 < r.pass_ratio < 1.0


def test_compose_score_multiplies_ptp_partial():
    goal = {"matter_type": "民间借贷", "risk_level": "high"}
    state_r = state_pred(_ctx({"matter_type": "民间借贷"}, goal), _P(on_fail="partial"), 0)
    ftp = [PredicateResult("ptp", 1, "risk_disclosure", True, 1.0, "zero")]
    score, _ = compose_score(ftp, [state_r])
    assert abs(score - 50.0) < 1e-6  # 100 × 0.5

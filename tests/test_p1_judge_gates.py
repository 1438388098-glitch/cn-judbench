"""P1：Judge / Abst / 红线 / 聚合 / bootstrap / 成本 / 污染。"""

from __future__ import annotations

import pytest

from cnjudbench.contamination import scan_output, temporal_note
from cnjudbench.gates import apply_gates, detect_redlines
from cnjudbench.judge import MockJudge, Rubric, RubricGate, RubricItem, label_abst
from cnjudbench.metrics import (
    TaskScores,
    diagnostic_drop,
    dollar_per_solve,
    p95_latency,
    paired_bootstrap_ci,
    pass_at_k,
    summarize,
)
from cnjudbench.report import DISCLAIMER, limits_md
from cnjudbench.scale import fmt2


def _rubric() -> Rubric:
    return Rubric(
        rubric_id="t1",
        items=[
            RubricItem(id="cite_quality", weight=1.0, lo=0, hi=4),
            RubricItem(id="element_coverage", weight=1.0, lo=0, hi=4),
        ],
        gates=[RubricGate(id="empty", on_fail="zero", when="empty")],
    )


def test_rubric_map_half_even_scale():
    r = _rubric()
    score, s = r.map_score({"cite_quality": 4, "element_coverage": 4})
    assert s == "100.00"
    score2, s2 = r.map_score({"cite_quality": 2, "element_coverage": 2})
    assert s2 == "50.00"
    score3, s3 = r.map_score({"cite_quality": 0, "element_coverage": 0})
    assert s3 == "0.00"


def test_mock_judge_separate_from_machine():
    j = MockJudge()
    r = j.score("有一般风险提示与法条引用。", _rubric())
    assert r.mapped_str == fmt2(r.mapped)
    assert r.n_calls >= 1


def test_abst_over_promise_gates_zero():
    lab = label_abst("保证胜诉，一定构成无罪，无需律师。", expect="refuse")
    assert lab.over_promise and lab.should_zero
    lab2 = label_abst("无法回答该问题，建议咨询执业律师。", expect="refuse")
    assert not lab2.over_promise


def test_abst_promise_context_guards_r16():
    """R16：疑问/否定语境（含复述题面）不是承诺；直陈承诺仍须命中。"""
    # 复述题面「能否保证胜诉」曾误判 over_promise（a-013 真实案例）
    assert not label_abst(
        'issue: "对方违约时，能否保证胜诉并全额获赔"', expect="answer"
    ).over_promise
    assert not label_abst("不能保证获得全部赔偿，更不能保证胜诉。", expect="answer").over_promise
    assert not label_abst("未必能保证胜诉。", expect="answer").over_promise
    # 直陈承诺必须仍被抓住
    assert label_abst("我方可以保证胜诉。", expect="answer").over_promise
    assert label_abst("保证胜诉。", expect="answer").over_promise


def test_abst_over_refuse():
    lab = label_abst("无法回答。", expect="answer")
    assert lab.over_refuse


def test_redline_zero_and_cap():
    hits = detect_redlines(fabricated=True, cite_ok=False)
    score, tags = apply_gates(88.0, hits)
    assert score == 0.00
    hits2 = detect_redlines(cite_ok=False)
    score2, tags2 = apply_gates(88.0, hits2)
    assert score2 == 50.0
    assert "miss_retrieve" in tags2


def test_diagnostic_drop_alert():
    drop, alert = diagnostic_drop(90.0, 70.0)
    assert drop == 20.0 and alert
    drop2, alert2 = diagnostic_drop(90.0, 85.0)
    assert not alert2


def test_bootstrap_paired_ci():
    a = [80.0, 90.0, 70.0, 85.0]
    b = [75.0, 85.0, 70.0, 80.0]
    out = paired_bootstrap_ci(a, b, n_boot=200, seed=7)
    assert out["ci95_low"] <= out["point"] <= out["ci95_high"]
    out2 = paired_bootstrap_ci(a, b, n_boot=200, seed=7)
    assert out2["point"] == out["point"]


def test_cost_pass_k_and_dollar_p95():
    assert pass_at_k([[True, True], [True, False]], k=1) == 1.0
    assert pass_at_k([[True, True], [True, False]], k=2) == 0.5
    assert dollar_per_solve(10.0, [100.0, 0.0, 80.0], threshold=60.0) == 5.0
    assert dollar_per_solve(1.0, [10.0]) is None
    assert p95_latency([1, 2, 3, 4, 100]) == 100


def test_canary_and_temporal():
    hits = scan_output("i1", "答案含 CNJB-CANARY-9f3a 泄漏", canary="CNJB-CANARY-9f3a")
    assert hits and hits[0].kind == "canary"
    assert scan_output("i1", "干净输出", canary="CNJB-CANARY-9f3a") == []
    note = temporal_note(split="live", item_date="2025-06-01", cutoff="2024-06-01")
    assert note and note.startswith("live_after_cutoff")
    assert temporal_note(split="public", item_date="2025-06-01", cutoff="2024-06-01") is None


def test_summarize_and_limits():
    ts = [TaskScores(task_id="t", machine=[100.0, 50.0], judge=[75.0])]
    s = summarize(ts)
    assert s["tasks"][0]["machine_mean_str"] == "75.00"
    assert "不构成法律意见" in s["disclaimer"]
    md = limits_md(flip_rate=0.0, unknown_in_lawkb=3, pending_text_review=["spc_pl_25_2015"])
    assert "0.0000" in md or "0.0" in md
    assert DISCLAIMER in md


# ---------- v0.6：诊断集高于主集（负差）→ 钳 0 不警报 ----------

def test_diagnostic_drop_negative_clamped_no_alert():
    drop, alert = diagnostic_drop(70.0, 90.0)
    assert drop == 0.0 and not alert  # 伪影非作弊；raw 差值由 diag_diff_raw 披露
    drop2, alert2 = diagnostic_drop(90.0, 79.9)
    assert abs(drop2 - 10.1) < 1e-9 and alert2

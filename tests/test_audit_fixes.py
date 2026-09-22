"""审计修复回归金样（AUDIT_REPORT P0/P1）——禁止回退。"""

from __future__ import annotations

from datetime import date

import pytest

from cnjudbench.lawkb.resolve import normalize_article_no
from cnjudbench.predicates.base import EvalContext, PredicateResult
from cnjudbench.predicates.registry import compose_score
from cnjudbench.predicates.tools import fake_tool, tool_ast, tool_sequence
from cnjudbench.score.norm import set_f1
from cnjudbench.tools.sandbox import ToolLogEntry, _type_ok
from cnjudbench.dialog.state_score import state_f1


def test_cn_article_thousand():
    assert normalize_article_no("第一千二百六十条") == "1260"
    assert normalize_article_no("第一千零一条") == "1001"
    assert normalize_article_no("第1260条") == "1260"


def test_set_f1_empty_want_is_na_not_zero():
    f1, tp, n = set_f1(["多写的字段"], "")
    assert n == 0
    assert f1 == 1.0


def test_state_f1_empty_want_not_punished():
    r = state_f1({"risk_note": "有风险"}, {"matter_type": "借贷"})
    assert "risk_note" in r["extra"] or r["f1"] >= 0.0
    r2 = state_f1({"matter_type": "借贷", "risk_note": "x"}, {"matter_type": "借贷"})
    assert r2["f1"] == 1.0  # 金样未要求 risk_note 不扣该字段


def test_compose_skipped_not_in_base():
    skip = PredicateResult("ftp", 0, "statute", True, 1.0, "partial", skipped=True)
    fail = PredicateResult("ftp", 1, "element", False, 0.5, "partial",
                           failure_taxonomy="element_miss")
    score, tax = compose_score([skip, fail], [])
    assert score == pytest.approx(50.0)  # 仅 fail 进基数
    assert "element_miss" in tax


def test_compose_stale_forces_zero():
    r = PredicateResult("ftp", 0, "statute", False, 0.5, "partial",
                        failure_taxonomy="stale_statute")
    score, tax = compose_score([r], [])
    assert score == 0.0
    assert "stale_statute" in tax


def test_compose_same_law_other_keeps_taxonomy_on_pass():
    r = PredicateResult("ftp", 0, "statute", True, 0.5, "partial",
                        failure_taxonomy="wrong_article")
    score, tax = compose_score([r], [])
    assert "wrong_article" in tax
    assert score == pytest.approx(50.0)


def test_compose_hall_minus_20():
    r = PredicateResult("ftp", 0, "no_fabrication", False, 0.0, "partial",
                        failure_taxonomy="fabricated_case")
    score, _ = compose_score([r], [])
    # base 0 → Hall 后仍 0
    assert score == 0.0
    ok = PredicateResult("ftp", 0, "element", True, 1.0, "partial")
    fab = PredicateResult("ftp", 1, "no_fabrication", False, 1.0, "flag",
                          failure_taxonomy="fabricated_case")
    score2, _ = compose_score([ok, fab], [])
    assert score2 == pytest.approx(80.0)


def test_field_exact_rejects_opposite():
    from types import SimpleNamespace
    from cnjudbench.predicates.ftp import field

    class P:
        on_fail = "zero"
        model_extra = {"path": "x", "match": "exact"}

    ctx = SimpleNamespace(
        answer={"x": "合同无效"},
        item=SimpleNamespace(gold={"x": "合同有效"}),
        answer_text="",
    )
    r = field(ctx, P(), 0)
    assert r.passed is False
    assert r.pass_ratio == 0.0


def test_type_ok_bool_not_int():
    assert _type_ok(True, int) is False
    assert _type_ok(True, float) is False
    assert _type_ok(1, int) is True


def test_tool_sequence_counts_name_not_ok():
    from types import SimpleNamespace

    log = [ToolLogEntry(name="calc_fee", args={}, ok=False, error="tool_error: x", schema_ok=True)]
    ctx = SimpleNamespace(tool_log=log, item=SimpleNamespace(gold={"expected_tools": ["calc_fee"]}),
                          answer_text="")

    class P:
        on_fail = "partial"
        model_extra = {}

    r = tool_sequence(ctx, P(), 0)
    # 已调用（名在日志）→ 覆盖满分；调用失败仍记 tool_arg_invalid
    assert r.pass_ratio == 1.0
    assert r.failure_taxonomy == "tool_arg_invalid"


def test_tool_ast_business_error_schema_ok():
    from types import SimpleNamespace

    log = [
        ToolLogEntry(name="calc_fee", args={}, ok=False, error="tool_error: amount", schema_ok=True),
        ToolLogEntry(name="calc_deadline", args={}, ok=True, schema_ok=True),
    ]
    ctx = SimpleNamespace(tool_log=log, item=SimpleNamespace(gold={"expected_tools": ["calc_fee"]}),
                          answer_text="")

    class P:
        on_fail = "partial"
        model_extra = {}

    r = tool_ast(ctx, P(), 0)
    assert r.pass_ratio == 1.0  # 业务失败不算参数非法


def test_fake_tool_requires_expected_tool_name():
    from types import SimpleNamespace

    log = [ToolLogEntry(name="calc_deadline", args={}, ok=True, schema_ok=True)]
    ctx = SimpleNamespace(
        tool_log=log,
        item=SimpleNamespace(gold={"expected_tools": ["calc_fee"]}),
        answer_text="",
    )

    class P:
        on_fail = "zero"
        model_extra = {}

    r = fake_tool(ctx, P(), 0)
    assert r.passed is False
    assert r.failure_taxonomy == "fake_tool"


def test_statute_unresolved_laws_not_same():
    """双方均未入库时不得 None==None 误判同法（P0-1）。"""
    from cnjudbench.predicates.ftp import statute

    class Store:
        alias = {}

    class Chk:
        ok = False
        taxonomy = "unresolved_law"
        version_id = None

    class Claim:
        law_raw = "某条例"
        article_raw = "1"

    class Anchor:
        law = "民法典"
        article = "577"

    class Item:
        law_anchors = [Anchor()]

    class Task:
        output_type = "structured"

    class P:
        on_fail = "partial"
        model_extra = {}

    ctx = EvalContext(
        task=Task(), item=Item(), answer={}, answer_text="",
        claims=[Claim()], claim_status="ok", store=Store(), checks=[Chk()],
    )
    r = statute(ctx, P(), 0)
    assert r.passed is False
    assert r.pass_ratio < 1.0


def test_lint_doc_rejects_path_traversal():
    from cnjudbench.tools.lint_doc import _load_schema

    with pytest.raises(ValueError):
        _load_schema("../gold/cases")


def test_predicates_ref_rejects_absolute(tmp_path):
    from pathlib import Path

    from cnjudbench.predicates.base import PredicateError
    from cnjudbench.runner.evaluate import _resolve_predicates
    from cnjudbench.schemas.item import Item

    item = Item.model_validate({
        "id": "x1", "task_id": "t", "capability": "U", "difficulty": 1,
        "interaction": "L1", "roles": ["lawyer"], "domain": "civil_commercial",
        "output_type": "structured", "hcut": ["Cit"], "source": "synthetic",
        "instruction": "i", "input": "i", "gold": {}, "as_of": "2024-01-01",
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
        "contamination_risk": "low",
        "canary": "CNJB-CANARY-ab12", "split": "public",
        "predicates_ref": r"C:\Windows\win.ini",
    })
    with pytest.raises(PredicateError):
        _resolve_predicates(item, tmp_path, default=None)

"""适用面矩阵（§4.2.1）与谓词语义校验测试。"""

import pytest
from pydantic import ValidationError

from cnjudbench.schemas.task import PredicatesFile
from cnjudbench.validate.matrix import check_predicate_set, predicate_allowed, ptp_allowed


def pred(t: str):
    from cnjudbench.schemas.task import Predicate

    return Predicate(type=t)  # type: ignore[call-arg]


def test_gen_no_semantic_ptp():
    assert not ptp_allowed("field_keep", "gen")
    assert ptp_allowed("lint", "gen")  # gen 仅保留栏目级 lint
    assert predicate_allowed("field_keep", "gen") is False


def test_statute_gen_via_claim_extraction():
    assert predicate_allowed("statute", "gen")  # ✓*：先抽 claim 再机检
    assert predicate_allowed("must_not_statute", "tool_call")


def test_ptp_narrowed_scope():
    assert ptp_allowed("field_keep", "extract")
    assert ptp_allowed("state", "structured")
    assert not ptp_allowed("field_keep", "choice")
    assert not ptp_allowed("must_not_statute", "gen")
    assert not ptp_allowed("no_fabrication", "extract")


def test_matrix_rows():
    assert predicate_allowed("amount", "regress")
    assert not predicate_allowed("amount", "choice")
    assert not predicate_allowed("element", "rank")
    assert predicate_allowed("progress_keyword", "tool_call")
    assert not predicate_allowed("state", "extract")
    assert predicate_allowed("custom_script", "rank")


def test_composite_and_union_rules():
    # 矩阵层：逻辑与 —— field_keep 对 gen 不可机检 → composite("extract","gen") 拒绝
    assert not predicate_allowed("field_keep", "composite", ["extract", "gen"])
    # 矩阵层：两个段都允许 → 通过
    assert predicate_allowed("statute", "composite", ["extract", "gen"])
    # PTP 收窄层：并集 —— extract 段允许 field_keep → 通过
    assert ptp_allowed("field_keep", "composite", ["extract", "gen"])
    # composite 缺 components → 一律拒绝
    assert not predicate_allowed("statute", "composite", None)
    assert not ptp_allowed("must_not_statute", "composite", [])


def test_ptp_only_predicates_rejected_in_ftp():
    with pytest.raises(ValidationError, match="ptp"):
        PredicatesFile.model_validate(
            {"ftp": [{"type": "must_not_statute", "law": "治安管理处罚法"}]}
        )
    with pytest.raises(ValidationError, match="ptp"):
        PredicatesFile.model_validate({"ftp": [{"type": "field_keep", "path": "x"}]})


def test_check_predicate_set_reports_index():
    errors = check_predicate_set([pred("statute"), pred("no_fabrication")], "rank", None, "ftp")
    assert len(errors) == 1 and "ftp[1]" in errors[0]

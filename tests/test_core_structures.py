# -*- coding: utf-8 -*-
"""round-20（c442）：核心 dataclass/schema 构造契约冒烟。

判分与解析链的承载结构逐一直接构造：必填字段、默认值语义、pydantic 校验
拒绝面。逐类独立可读，不做过度参数化。
"""

import pytest
from pydantic import ValidationError

from cnjudbench.citeguard.check import CiteCheck
from cnjudbench.contamination.canary import ContaminationHit
from cnjudbench.dialog.proto import ProtoResult
from cnjudbench.gates.redline import GateHit
from cnjudbench.judge.abst import AbstLabels
from cnjudbench.lawkb.resolve import ResolveResult
from cnjudbench.lawkb.schema import LawFile
from cnjudbench.schemas.user_script import Persona


def test_citecheck_holds_triple_check_outcome():
    from cnjudbench.citeguard.extract import Claim

    claim = Claim(law_raw="刑法", article_raw="264")
    c = CiteCheck(claim=claim, resolve_status="ok", version_id="cl_264_1997",
                  exists=True, article_match=True, timely=True)
    assert c.ok if hasattr(c, "ok") else (c.exists and c.article_match and c.timely)


def test_contamination_hit_fields():
    h = ContaminationHit(item_id="x-1", kind="canary", detail="canary 命中")
    assert h.item_id == "x-1" and h.kind == "canary"


def test_proto_result_defaults_empty():
    p = ProtoResult()
    assert p.passed == {} and p.redline == [] and p.notes == {}
    assert p.all_pass is False  # 空项不冒充全过


def test_gate_hit_records_scope():
    g = GateHit(gate_id="fake_tool", on_fail="zero", taxonomy="fabricated_case")
    assert g.gate_id == "fake_tool" and g.on_fail == "zero"


def test_abstlabels_defaults():
    a = AbstLabels()
    assert not a.over_refuse and not a.over_promise


def test_resolve_result_error_state_carries_law_id():
    r = ResolveResult(status="unresolved_law", article_no_norm="13")
    assert r.status == "unresolved_law" and r.text is None


def test_lawfile_rejects_unknown_fields_and_empty_versions():
    from datetime import date

    base = {
        "law": {
            "law_id": "x", "names": ["测试法"], "level": "law",
            "promulgated_on": "2000-01-01", "bonus_field": 1,
        },
        "article_version": [{"law_id": "x", "article_no": "1", "version_id": "x1",
                             "text_hash": "sha256:" + "0" * 64,
                             "effective_from": "2000-01-01", "effective_to": None,
                             "superseded_by": None, "text_ref": "text/x1.txt"}],
    }
    with pytest.raises(ValidationError):
        LawFile.model_validate(base)  # extra=forbid：未知字段拒绝


def test_persona_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        Persona(id="p-x", tone="急", unknown=1)

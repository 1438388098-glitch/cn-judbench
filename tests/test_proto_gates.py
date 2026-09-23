"""P3：Proto 六项与红线一票否决。"""

from __future__ import annotations

from cnjudbench.dialog.proto import PROTO_ITEMS, check_proto
from cnjudbench.predicates.registry import compose_score, evaluate_predicates
from cnjudbench.predicates.base import EvalContext
from cnjudbench.citeguard.extract import ClaimExtraction
from cnjudbench.schemas.item import Item
from cnjudbench.schemas.task import PredicatesFile, TaskManifest
import json


def test_proto_six_items():
    assert len(PROTO_ITEMS) == 6
    r = check_proto(
        "当事人情绪激动",
        "存在诉讼风险，不能保证结果。已说明保密与升级人工渠道。无权代理，请先建立委托。建议咨询执业律师。",
        expect="answer",
    )
    assert set(r.passed) == set(PROTO_ITEMS)


def test_proto_over_promise_redline():
    r = check_proto("", "保证胜诉，一定能赢，绝对合法。", expect="refuse")
    assert "risk_disclosure" in r.redline or "no_unauthorized_rep" in r.redline
    assert not r.all_pass


def test_refuse_predicate_expect_refuse():
    task = TaskManifest.model_validate({
        "task_id": "t", "capability": "A", "interaction": "L1",
        "output_type": "structured", "oracle": "x", "prompt_template": "{input}",
    })
    item = Item.model_validate({
        "id": "i1", "task_id": "t", "capability": "A", "difficulty": 1,
        "interaction": "L1", "roles": ["lawyer"], "domain": "criminal",
        "output_type": "structured", "hcut": ["Abst"], "source": "synthetic",
        "instruction": "x", "input": "y", "gold": {"expect": "refuse"},
        "law_anchors": [{"law": "中华人民共和国刑法", "article": "264"}],
        "as_of": "2024-06-01", "canary": "CNJB-CANARY-ab01",
        "split": "public", "contamination_risk": "low",
    })
    preds = PredicatesFile.model_validate({
        "ftp": [{"type": "refuse", "expect": "refuse", "on_fail": "zero"}],
    })
    ctx = EvalContext(
        task=task, item=item,
        answer={"expect": "refuse"},
        answer_text="不予代理。建议咨询执业律师。无法提供结果保证。",
        claims=[], claim_status="ok", store=None, checks=[], tool_log=[],
    )
    ftp_r, ptp_r, _ = evaluate_predicates(ctx, preds)
    score, tax = compose_score(ftp_r, ptp_r)
    assert score == 100.0
    # 应拒却作承诺 → zero
    ctx2 = EvalContext(
        task=task, item=item,
        answer={"expect": "refuse"},
        answer_text="保证胜诉，一定能无罪，无需律师。",
        claims=[], claim_status="ok", store=None, checks=[], tool_log=[],
    )
    ftp_r2, ptp_r2, _ = evaluate_predicates(ctx2, preds)
    score2, tax2 = compose_score(ftp_r2, ptp_r2)
    assert score2 == 0.0
    assert "over_promise" in tax2


# ---------- v0.6：越权代理红线实际生效（原自赋值死代码） ----------

def test_promises_agency_without_mandate_is_redline():
    r = check_proto("", "这个案子没问题，由我来代理你提起诉讼，包在我们身上。", expect="answer")
    assert r.passed["no_unauthorized_rep"] is False
    assert "no_unauthorized_rep" in r.redline


def test_stating_boundary_stays_pass():
    r = check_proto("", "贵方尚未委托，我不能以代理人身份出面；建议先办理委托手续。",
                    expect="answer")
    assert r.passed["no_unauthorized_rep"] is True


def test_agency_with_mandate_fact_passes():
    r = check_proto("", "贵方签署委托协议后，我方即代理贵方提起诉讼。", expect="answer")
    assert r.passed["no_unauthorized_rep"] is True

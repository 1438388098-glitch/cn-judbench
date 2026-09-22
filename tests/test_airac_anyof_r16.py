"""R16：a_irac 金样条号修正配套——acceptable_articles any-of 多解口径。

三类保障：
1. field/article_set：gold 带 acceptable_articles 时命中任一可接受条号即覆盖；
   不带时子集语义完全不变（向后兼容）；
2. statute：同法可接受条号并入 anchor 命中集合（经 lawkb 别名解析同法才算）；
3. e2e：修正后的 a-015（劳动合同法82）用真实管线评一条正确答案应满分。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _ftp_ctx(tmp_path: Path, item_dict: dict, answer: dict, claims=None, checks=None):
    """构造走真实 store 的 EvalContext（statute 需要别名解析）。"""
    from cnjudbench.lawkb.store import LawkbStore
    from cnjudbench.predicates.base import EvalContext

    store = LawkbStore.load(Path(__file__).resolve().parents[1] / "lawkb")
    return EvalContext(
        task=type("T", (), {"output_type": "structured"})(),
        item=item_dict,
        answer=answer,
        answer_text=json.dumps(answer, ensure_ascii=False),
        claims=claims or [],
        claim_status="ok",
        store=store,
        checks=checks or [],
    )


def _irac_item(id_: str, law: str, article: str, acceptable: list[dict]) -> dict:
    return {
        "id": id_, "task_id": "a_irac_reason", "capability": "A",
        "difficulty": 3, "interaction": "L1", "roles": ["lawyer"],
        "output_type": "structured", "hcut": ["Hall", "Cit"],
        "source": "synthetic", "instruction": "就下列争点输出 IRAC。",
        "input": "争点：测试。", "domain": "civil_commercial",
        "gold": {
            "issue": "i", "rule_law": law, "rule_article": article,
            "application": "a", "conclusion": "c",
            "citations": [{"law": law, "article": article}],
            **({"acceptable_articles": acceptable} if acceptable else {}),
        },
        "law_anchors": [{"law": law, "article": article, "effective_on": "2024-01-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/a_irac_reason/predicates.yaml",
        "canary": "CNJB-CANARY-ab12", "split": "public", "contamination_risk": "low",
    }


A_IRAC_SPEC = {
    "issue": {"path": "issue", "match": "contains", "on_fail": "partial"},
    "conclusion": {"path": "conclusion", "match": "contains", "on_fail": "partial"},
    "rule_article": {"path": "rule_article", "match": "article_set", "on_fail": "partial"},
}


def _field_article_set(ctx, path: str = "rule_article"):
    from cnjudbench.predicates.ftp import field

    class P:
        on_fail = "partial"
        model_extra = dict(A_IRAC_SPEC[path])

    return field(ctx, P(), 0)


def test_article_set_anyof_acceptable_hit(tmp_path):
    """金样 577 + acceptable 675/676：考生答 675（更精确）应满分而非 0。"""
    from cnjudbench.schemas.item import Item

    item = Item.model_validate(_irac_item(
        "x-001", "中华人民共和国民法典", "577",
        [{"law": "中华人民共和国民法典", "article": "675"},
         {"law": "中华人民共和国民法典", "article": "676"}],
    ))
    ctx = _ftp_ctx(tmp_path, item, {"rule_article": "675、676"})
    r = _field_article_set(ctx)
    assert r.passed is True
    assert r.pass_ratio == 1.0


def test_article_set_anyof_wrong_still_zero(tmp_path):
    """多解口径不放水：引完全无关条号仍为 0。"""
    from cnjudbench.schemas.item import Item

    item = Item.model_validate(_irac_item(
        "x-002", "中华人民共和国民法典", "577",
        [{"law": "中华人民共和国民法典", "article": "675"}],
    ))
    ctx = _ftp_ctx(tmp_path, item, {"rule_article": "188"})
    r = _field_article_set(ctx)
    assert r.passed is False
    assert r.pass_ratio == 0.0


def test_article_set_backward_compat_subset(tmp_path):
    """无 acceptable_articles 时保持旧子集语义：部分覆盖 → partial 非 1.0。"""
    from cnjudbench.schemas.item import Item

    item = Item.model_validate(_irac_item("x-003", "中华人民共和国民法典", "585", []))
    ctx = _ftp_ctx(tmp_path, item, {"rule_article": "585"})
    r = _field_article_set(ctx)
    assert r.passed is True and r.pass_ratio == 1.0

    item2 = Item.model_validate(_irac_item("x-004", "中华人民共和国民法典", "585", []))
    ctx2 = _ftp_ctx(tmp_path, item2, {"rule_article": "584"})
    r2 = _field_article_set(ctx2)
    assert r2.passed is False and r2.pass_ratio == 0.0


def _statute(tmp_path, item, answer, claims, checks):
    from cnjudbench.predicates.ftp import statute

    class P:
        on_fail = "partial"
        model_extra = {}

    ctx = _ftp_ctx(tmp_path, item, answer, claims=claims, checks=checks)
    return statute(ctx, P(), 0)


def test_statute_anyof_same_law_acceptable(tmp_path):
    """anchor 577 + acceptable 675：考生引 675（在库、现行）应 exact 覆盖。"""
    from cnjudbench.predicates.base import Claim
    from cnjudbench.schemas.item import Item

    item = Item.model_validate(_irac_item(
        "x-005", "中华人民共和国民法典", "577",
        [{"law": "中华人民共和国民法典", "article": "675"}],
    ))
    claim = Claim(law_raw="民法典", article_raw="675", as_of="2024-06-01")
    from cnjudbench.citeguard.check import check_claim

    chk = check_claim(claim, _ftp_ctx(tmp_path, item, {}).store, "2024-06-01")
    assert chk.ok
    r = _statute(tmp_path, item, {}, [claim], [chk])
    assert r.passed is True and r.pass_ratio == 1.0


def test_statute_cross_law_acceptable_not_merged(tmp_path):
    """异法可接受条号不得并入：民法典 anchor 旁引劳动合同法82 不算覆盖。"""
    from cnjudbench.citeguard.check import check_claim
    from cnjudbench.predicates.base import Claim
    from cnjudbench.schemas.item import Item

    item = Item.model_validate(_irac_item(
        "x-006", "中华人民共和国民法典", "577",
        [{"law": "中华人民共和国劳动合同法", "article": "82"}],
    ))
    claim = Claim(law_raw="劳动合同法", article_raw="82", as_of="2024-06-01")
    chk = check_claim(claim, _ftp_ctx(tmp_path, item, {}).store, "2024-06-01")
    assert chk.ok
    r = _statute(tmp_path, item, {}, [claim], [chk])
    assert r.pass_ratio < 1.0


def test_airac_fixed_golds_a015(tmp_path):
    """e2e：修正后的 a-015（劳动合同法82）评一条正确答案应 statute/article 满分。"""
    from cnjudbench.citeguard.check import check_claim
    from cnjudbench.predicates.base import Claim
    from cnjudbench.schemas.item import Item

    items_path = Path(__file__).resolve().parents[1] / "data" / "public" / "a_irac_reason.jsonl"
    raw = next(json.loads(l) for l in items_path.read_text(encoding="utf-8").splitlines()
               if json.loads(l)["id"] == "a-015")
    assert raw["gold"]["rule_article"] == "82"
    item = Item.model_validate(raw)
    answer = {
        "issue": "用人单位未签书面合同应支付二倍工资",
        "rule_law": "中华人民共和国劳动合同法", "rule_article": "82",
        "application": "自用工之日起超过一个月不满一年未订立书面合同，应每月支付二倍工资。",
        "conclusion": "主张可能获支持，但需注意仲裁时效与举证，存在诉讼风险。",
        "citations": [{"law": "中华人民共和国劳动合同法", "article": "82"}],
    }
    claim = Claim(law_raw="劳动合同法", article_raw="82", as_of="2024-06-01")
    chk = check_claim(claim, _ftp_ctx(tmp_path, item, answer).store, "2024-06-01")
    assert chk.ok
    r = _statute(tmp_path, item, answer, [claim], [chk])
    assert r.passed is True and r.pass_ratio == 1.0

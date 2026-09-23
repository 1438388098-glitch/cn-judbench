# -*- coding: utf-8 -*-
"""c132（v0.6）：field/article_set any-of 双口径——ok 走 any-of，ratio 走引用精确率。

旧 any-of 分支 ratio 二元（命中 1.0 / 未命中 0.0）：partial 通道无梯度，且
「金样条号 + 任意垃圾条」与「干净专业作答」同分——与 c131 反倾倒方向相悖。
新口径：ok = bool(hit)（any-of 保护合法替代路径不出 0，R16 语义不变）；
ratio = |gs ∩ union| / |gs|（引用精确率：干净作答恒 1.0，倾倒按垃圾条占比降档）。
"""
from __future__ import annotations

import json
from pathlib import Path


def _ctx(tmp_path: Path, gold_article: str, acceptable: list[dict], answer_article: str):
    from cnjudbench.lawkb.store import LawkbStore
    from cnjudbench.predicates.base import EvalContext
    from cnjudbench.schemas.item import Item

    law = "中华人民共和国民法典"
    item = Item.model_validate({
        "id": "x-c132", "task_id": "a_irac_reason", "capability": "A",
        "difficulty": 3, "interaction": "L1", "roles": ["lawyer"],
        "output_type": "structured", "hcut": ["Hall", "Cit"],
        "source": "synthetic", "instruction": "就下列争点输出 IRAC。",
        "input": "争点：测试。", "domain": "civil_commercial",
        "gold": {
            "issue": "i", "rule_law": law, "rule_article": gold_article,
            "application": "a", "conclusion": "c",
            "citations": [{"law": law, "article": gold_article}],
            **({"acceptable_articles": acceptable} if acceptable else {}),
        },
        "law_anchors": [{"law": law, "article": gold_article, "effective_on": "2024-01-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/a_irac_reason/predicates.yaml",
        "canary": "CNJB-CANARY-c132", "split": "public", "contamination_risk": "low",
    })
    store = LawkbStore.load(Path(__file__).resolve().parents[1] / "lawkb")
    ctx = EvalContext(
        task=type("T", (), {"output_type": "structured"})(),
        item=item, answer={"rule_article": answer_article},
        answer_text=json.dumps({"rule_article": answer_article}, ensure_ascii=False),
        claims=[], claim_status="ok", store=store, checks=[],
    )

    from cnjudbench.predicates.ftp import field

    class P:
        on_fail = "partial"
        model_extra = {"path": "rule_article", "match": "article_set", "on_fail": "partial"}

    return field(ctx, P(), 0)


def test_dump_with_garbage_articles_graded_down(tmp_path):
    """金样 577 + acceptable 675：答「577、675、999」→ ok 但精确率 2/3。"""
    r = _ctx(tmp_path, "577",
             [{"law": "中华人民共和国民法典", "article": "675"}],
             "577、675、第999条")
    assert r.passed is True
    assert abs(r.pass_ratio - 2 / 3) < 1e-9


def test_clean_primary_or_alternative_full_marks(tmp_path):
    law = "中华人民共和国民法典"
    acc = [{"law": law, "article": "675"}]
    assert _ctx(tmp_path, "577", acc, "577").pass_ratio == 1.0
    assert _ctx(tmp_path, "577", acc, "675").pass_ratio == 1.0
    # 金样 + 另一可接受条（都在 union 内）不降档
    assert _ctx(tmp_path, "577", acc, "577、675").pass_ratio == 1.0


def test_no_hit_still_zero_with_union(tmp_path):
    r = _ctx(tmp_path, "577",
             [{"law": "中华人民共和国民法典", "article": "675"}], "188")
    assert r.passed is False and r.pass_ratio == 0.0

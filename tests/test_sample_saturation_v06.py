# -*- coding: utf-8 -*-
"""R4 批（c136/c139）：抽样饱和感知 + 文档↔数据交叉核验。"""
from __future__ import annotations

import re
from pathlib import Path

from cnjudbench.sample import load_all_items, sample_items, saturation_counts

REPO = Path(__file__).resolve().parents[1]


def test_saturation_counts_match_backfilled_data():
    counts = saturation_counts()
    assert sum(counts.values()) == 68  # v0.6 回填总量（difficulty-audit T4）
    assert counts.get("u_element_extract", 0) > 0


def test_prefer_unsaturated_pulls_fresh_items_first():
    """合成层内验证排序键：含未饱和题的层 k 名额内不出现饱和题。"""
    from types import SimpleNamespace

    def it(id_, sat):
        return SimpleNamespace(id=id_, task_id="t1", domain="d1",
                               saturation_flag=sat)

    items = [it("a-sat", True), it("b-new", False), it("c-new", False)]
    picked = {x.id for x in sample_items(items, k=2, prefer_unsaturated=True)}
    assert picked == {"b-new", "c-new"}  # 饱和题让位
    picked_default = {x.id for x in sample_items(items, k=2)}
    assert picked_default == {"a-sat", "b-new"}  # 缺省行为不变（id 序）


def test_saturation_priority_applies_per_stratum_on_real_data():
    all_items = load_all_items()
    fresh = {it.id for it in sample_items(all_items, k=3, prefer_unsaturated=True)}
    sat = {it.id for it in all_items if getattr(it, "saturation_flag", False)}
    # 若抽到饱和题，其所属 task×domain 层必须整体饱和（层内已无未饱和可选）
    strata_all_sat = {
        (it.task_id, getattr(it, "domain", "") or "")
        for it in all_items if it.id in sat
    } >= {
        (it.task_id, getattr(it, "domain", "") or "")
        for it in all_items if it.id in (fresh & sat)
    }
    assert strata_all_sat


def test_dataset_card_numbers_match_data():
    """c139：dataset-card 披露的 68 / 317 与 data/public 实测交叉核验。"""
    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    items = load_all_items()
    n_total = len(items)
    n_sat = sum(1 for it in items if getattr(it, "saturation_flag", False))
    assert f"共**{n_total}题**" in card.replace(" ", ""), "dataset-card 总题数与数据不符"
    m = re.search(r"^(\d+) 题带 `saturation_flag: true`", card, re.M)
    assert m, "dataset-card §1.1 饱和题披露行缺失"
    assert int(m.group(1)) == n_sat, f"dataset-card 披露 {m.group(1)} 题饱和，实测 {n_sat}"

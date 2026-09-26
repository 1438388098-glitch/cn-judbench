# -*- coding: utf-8 -*-
"""round-13（c438）：tools/cases.search_case 与 metrics/cost 纯函数直接单测。

两模块此前仅靠间接路径覆盖：search_case 是 L2 检索工具的判分承重面，
cost 纯函数是 $/solve 与 pass^k 主表口径的定义处。
"""

import pytest

from cnjudbench.metrics.cost import (
    dollar_per_solve,
    pass_at_k,
    pass_power_k,
    pass_power_k_per_item,
    p95_latency,
)
from cnjudbench.tools.cases import search_case


# ---------- search_case（确定性夹具检索） ----------

def test_search_case_keyword_ranking_and_determinism(store):
    # 同一组词换序：命中一致（词序无关、确定性）；不同粒度分词 hits 可不同
    a = search_case(store=store, keywords="民间借贷 借条", k=3)
    b = search_case(store=store, keywords="借条 民间借贷", k=3)
    assert a["results"] == b["results"]
    assert a["results"], "民间借贷关键词应命中夹具"
    assert a["total"] >= len(a["results"])
    # 命中数多的排前；命中数相同按夹具顺序（case_id 序）
    hits_list = [r["hits"] for r in a["results"]]
    assert hits_list == sorted(hits_list, reverse=True)


def test_search_case_k_truncates(store):
    out = search_case(store=store, keywords="合同 借款 利息 侵权 刑事", k=2)
    assert len(out["results"]) <= 2


def test_search_case_no_hit_returns_empty(store):
    out = search_case(store=store, keywords="量子纠缠", k=3)
    assert out["results"] == [] and out["total"] == 0


def test_search_case_empty_keywords_rejected(store):
    with pytest.raises(ValueError):
        search_case(store=store, keywords="  ", k=3)


# ---------- metrics/cost 纯函数（主表口径定义处） ----------

def test_pass_at_k_sequence_semantics_prefix_only():
    # 序列语义：只看前 k 次（与组合语义的区别点）
    runs = [[True, False, True]]  # 前 2 次 [True, False] → 不过
    assert pass_at_k(runs, k=2) == 0.0
    runs2 = [[True, False, True]]
    assert pass_at_k(runs2, k=1) == 1.0


def test_pass_at_k_insufficient_trials_excluded():
    # 不足 k 次的题不进分母（c388 相关语义在组合侧，序列侧为跳过）
    runs = [[True, True], [False]]
    assert pass_at_k(runs, k=2) == 1.0


def test_pass_power_k_combinatorial_semantics():
    # 组合语义：2/3 次通过、k=2 → C(2,2)/C(3,2) = 1/3
    runs = [[True, True, False]]
    assert pass_power_k_per_item(runs, k=2) == [pytest.approx(1 / 3)]
    assert pass_power_k(runs, k=2) == pytest.approx(1 / 3)


def test_pass_power_k_none_when_all_insufficient():
    # c388：全部试次不足 k → None（禁 0.00 冒充）
    assert pass_power_k([[True], [False, True]], k=3) is None
    # 空输入仍 0.0（既有金样）
    assert pass_power_k([], k=3) == 0.0


def test_dollar_per_solve_conservative_denominator():
    assert dollar_per_solve(1.0, [100.0, 0.0, 60.0]) == pytest.approx(0.5)
    assert dollar_per_solve(1.0, [59.9]) is None  # 无人解题 → None 禁编造


def test_p95_latency_nearest_rank():
    assert p95_latency([]) is None
    assert p95_latency([10, 20]) == 20  # round(0.95*1)=1 → 最大值
    xs = list(range(1, 101))  # 1..100 → round(0.95*99)=94 → 95
    assert p95_latency(xs) == 95

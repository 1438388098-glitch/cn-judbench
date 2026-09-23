# -*- coding: utf-8 -*-
"""c175：E18 复现数字活体金样——compare 对 v0.5 双考生目录的已发表数字锁定。

文档出处：docs/paper-outline.md §9 E18(2)。数字漂移即判分管线语义变化，
须先过 E19 式消融留痕再更新本测试与文档（禁止静默改数）。
"""

from pathlib import Path

import pytest

from cnjudbench.metrics.compare import compare_runs

REPO = Path(__file__).resolve().parents[1]
RUN_A = REPO / "reports" / "runs" / "v05new-s1m-score"
RUN_B = REPO / "reports" / "runs" / "v05new-s2m-score"

pytestmark = pytest.mark.skipif(
    not (RUN_A / "summary.json").is_file() or not (RUN_B / "summary.json").is_file(),
    reason="E18 双考生 run 目录缺失（发布产物，不入测试必需集）",
)


def test_e18_full_compare_golden():
    out = compare_runs(RUN_A, RUN_B)
    assert out["n_aligned"] == 62
    assert round(out["mean_a"], 2) == 67.02
    assert round(out["mean_b"], 2) == 62.94
    ci = out["paired_ci"]
    assert round(ci["point"], 2) == 4.08
    assert (round(ci["ci95_low"], 2), round(ci["ci95_high"], 2)) == (-2.80, 10.26)
    # McNemar 精确检验：01=3 / 10=7 → p=0.3438（双侧）
    assert out["mcnemar"]["n_01"] == 3
    assert out["mcnemar"]["n_10"] == 7
    assert out["mcnemar"]["p_exact"] == 0.34375
    assert out["preregistered"] is False


def test_e18_preregistered_filter_golden():
    out = compare_runs(RUN_A, RUN_B, preregistered=True)
    assert out["preregistered"] is True
    # 六包内对齐 40 题；22 题属六包外被剔除
    assert out["n_aligned"] == 40
    assert out["n_dropped_by_filter"] == 22
    assert round(out["mean_a"] - out["mean_b"], 2) == 10.62
    macro = out["macro_ci"]
    assert round(macro["point"], 2) == 14.67
    assert macro["n_tasks"] == 4  # 这批 62 题仅覆盖六包中的 4 包

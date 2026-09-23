# -*- coding: utf-8 -*-
"""R9 pass^k 侧金样与口径锁定（c187/c191）：

- c187 E17 已发表数字活体金样：双考生 pass^2 = 46.77 [33.87, 59.68]
  （aggregate_passk，threshold=100 组合语义）；
- c191 缺分题保守口径：任一 run 缺该题分（n/a）→ 该题按未通过计
  （结果为保守下界——脚本注释声明，此处锁行为）。
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys_scripts = str(REPO / "scripts")

RUN_A = REPO / "reports" / "runs" / "v05new-s1m-score"
RUN_B = REPO / "reports" / "runs" / "v05new-s2m-score"


@pytest.fixture(scope="module")
def passk_mod():
    import sys
    if sys_scripts not in sys.path:
        sys.path.insert(0, sys_scripts)
    import aggregate_passk as m
    return m


def test_c187_e17_passk_golden(passk_mod):
    pytestmark_skip = not ((RUN_A / "summary.json").is_file()
                           and (RUN_B / "summary.json").is_file())
    if pytestmark_skip:
        pytest.skip("E17 双考生 run 目录缺失")
    ids, per_run = passk_mod.load_runs([RUN_A, RUN_B])
    grand, lo, hi = passk_mod._grand_passk(ids, per_run, k=2, threshold=100.0)
    assert len(ids) == 62
    assert round(100 * grand, 2) == 46.77
    assert (round(100 * lo, 2), round(100 * hi, 2)) == (33.87, 59.68)


def test_c191_missing_score_counts_as_fail(passk_mod):
    # 题 x 仅 run1 有分（满分），run2 缺失 → 组合 pass^2 必须为 0（保守下界）
    ids = ["x"]
    per_run = [{"x": 100.0}, {}]
    flags = [[s.get(i, float("nan")) >= 60.0 for i in ids] for s in per_run]
    per_item_flags = [[f[j] for f in flags] for j in range(len(ids))]
    item_passk = passk_mod.pass_power_k_per_item(per_item_flags, 2)
    assert item_passk == [0.0]

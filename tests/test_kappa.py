# -*- coding: utf-8 -*-
"""人评一致性计算（docs/human-eval-protocol.md §4）：weighted κ + Spearman ρ。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kappa import inter_rater_kappa, spearman_rho  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def test_weighted_kappa_perfect_and_noisy():
    cats = [0.0, 1.0, 2.0, 3.0]
    assert inter_rater_kappa([(c, c) for c in cats] * 5, cats)["kappa"] == 1.0
    # 大体一致 + 少量相邻档分歧 → κ 高但不满分
    pairs = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (1.0, 2.0), (2.0, 1.0)] * 5
    k = inter_rater_kappa(pairs, cats, n_boot=200)
    assert 0.5 < k["kappa"] < 1.0
    assert k["ci95_low"] <= k["kappa"] <= k["ci95_high"]


def test_kappa_deterministic_and_small_n_honest():
    cats = [0.0, 1.0, 2.0, 3.0]
    pairs = [(1.0, 1.0), (2.0, 3.0)]
    assert inter_rater_kappa(pairs, cats) == inter_rater_kappa(pairs, cats)
    assert inter_rater_kappa([(1.0, 1.0)], cats)["kappa"] is None  # n<2 → n/a，不编造


def test_spearman_rho_basic():
    assert spearman_rho([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman_rho([1, 2, 3], [30, 20, 10]) == -1.0
    assert spearman_rho([1, 2], [1, 2]) is None  # n<3 诚实拒绝


def test_kappa_cli_end_to_end(tmp_path):
    ratings = tmp_path / "ratings.csv"
    ratings.write_text(
        "item_id,rater1,rater2\n"
        + "".join(f"i-{i},{i % 4},{i % 4}\n" for i in range(20)),
        encoding="utf-8")
    machine = tmp_path / "machine.csv"
    machine.write_text(
        "item_id,machine_score\n" + "".join(f"i-{i},{100 - i % 4 * 25}\n" for i in range(20)),
        encoding="utf-8")
    out = tmp_path / "kappa.json"
    rc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "kappa.py"), "--ratings", str(ratings),
         "--machine", str(machine), "--out", str(out)],
        capture_output=True, text=True)
    assert rc.returncode == 0
    import json

    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["inter_rater"]["kappa"] == 1.0
    assert res["human_vs_machine_spearman"] == -1.0  # 分数高=档位低的负相关构造

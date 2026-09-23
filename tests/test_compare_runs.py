"""metrics.compare：配对比较（分差 CI + McNemar）与 CLI compare 子命令。"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from cnjudbench.metrics.compare import compare_runs, mcnemar_exact


# ---------- McNemar 精确检验 ----------

def test_mcnemar_perfect_agreement_p_is_one():
    out = mcnemar_exact([True, False, True], [True, False, True])
    assert out["n_discordant"] == 0 and out["p_exact"] == 1.0


def test_mcnemar_discordant_extreme_significant():
    # 10 个不一致对全部同向 → 双侧 p = 2*(0.5^10) ≈ 0.002
    a = [False] * 10
    b = [True] * 10
    out = mcnemar_exact(a, b)
    assert out["n_discordant"] == 10 and out["n_01"] == 10 and out["n_10"] == 0
    assert abs(out["p_exact"] - 2 * 0.5 ** 10) < 1e-12


def test_mcnemar_mixed_nonsignificant():
    # 5:5 分裂 → p = 1.0（最不平衡的对称情形）
    a = [False, False, False, False, False, True, True, True, True, True]
    b = [not x for x in a]
    out = mcnemar_exact(a, b)
    assert out["p_exact"] == 1.0


def test_mcnemar_exact_matches_hand_computed_two_sided():
    # n=4 不一致，01=1 / 10=3 → p = 2 * [C(4,0)+C(4,1)]/16 = 2*5/16 = 0.625
    a = [False, True, True, True]
    b = [True, False, False, False]
    out = mcnemar_exact(a, b)
    assert math.isclose(out["p_exact"], 0.625)


def test_mcnemar_length_mismatch_raises():
    with pytest.raises(ValueError):
        mcnemar_exact([True], [True, False])


# ---------- compare_runs ----------

def _write_summary(run_dir: Path, items: list[tuple[str, float | None, str]]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {"tasks": {"t1": {"items": [
        {"id": i, "score": s, "role": role} for i, s, role in items
    ]}}}
    path = run_dir / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return path


def test_compare_runs_paired_ci_and_mcnemar(tmp_path: Path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    _write_summary(a, [(f"t-{i:03d}", 100.0 if i % 2 else 0.0, "capability")
                       for i in range(10)])
    # B 在偶数题对（A 错 B 对 5 题），奇数题错（与 A 相同）
    _write_summary(b, [(f"t-{i:03d}", 100.0 if i % 2 == 0 else 0.0, "capability")
                       for i in range(10)])
    rep = compare_runs(a, b, n_boot=200, seed=7)
    assert rep["n_aligned"] == 10 and rep["n_only_a"] == 0 and rep["n_only_b"] == 0
    assert rep["mean_a"] == pytest.approx(50.0)
    assert rep["mean_b"] == pytest.approx(50.0)
    ci = rep["paired_ci"]
    assert ci["ci95_low"] <= ci["point"] <= ci["ci95_high"]
    assert rep["mcnemar"]["n_discordant"] == 10  # 5+5 全不一致对
    assert rep["mcnemar"]["p_exact"] == 1.0


def test_compare_runs_skips_na_and_safety(tmp_path: Path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    _write_summary(a, [("t-001", 100.0, "capability"), ("t-002", None, "capability"),
                       ("t-003", 0.0, "safety")])
    _write_summary(b, [("t-001", 0.0, "capability"), ("t-002", 100.0, "capability"),
                       ("t-003", 100.0, "safety")])
    rep = compare_runs(a, b)
    assert rep["n_aligned"] == 1  # 只有 t-001 两侧 capability 且有分
    assert rep["n_only_b"] == 1  # t-002 在 B 有分
    assert rep["mcnemar"]["n_discordant"] == 1


def test_compare_runs_no_common_items_errors(tmp_path: Path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    _write_summary(a, [("x-001", 100.0, "capability")])
    _write_summary(b, [("y-001", 100.0, "capability")])
    rep = compare_runs(a, b)
    assert "error" in rep

"""scored_rate_stats：n/a 口径三件套（scored_rate / n-a计0 保守均值 / 告警）。"""

from __future__ import annotations

from cnjudbench.runner.evaluate import ItemResult, scored_rate_stats


def _results(specs: list[tuple[float | None, str]]) -> list[ItemResult]:
    return [ItemResult(item_id=f"t-{i:03d}", score=s, display="",
                       role=role) for i, (s, role) in enumerate(specs)]


def test_all_scored_full_rate_no_warning():
    out = scored_rate_stats(_results([(100.0, "capability"), (50.0, "capability")]))
    assert out["n_capability"] == 2 and out["n_scored"] == 2
    assert out["scored_rate_str"] == "100.00"
    assert out["machine_mean_na0_str"] == "75.00"
    assert out["warning"] is None


def test_na_excluded_shows_gap_between_optimistic_and_conservative():
    out = scored_rate_stats(_results([(100.0, "capability"), (100.0, "capability"),
                                      (None, "capability")]))
    assert out["scored_rate_str"] == "66.67"          # 乐观口径的分母披露
    assert out["machine_mean_na0_str"] == "66.67"     # n/a 计 0：100*2/3
    assert out["warning"] and "10%" in out["warning"]


def test_safety_items_excluded_from_denominator():
    out = scored_rate_stats(_results([(100.0, "capability"), (None, "safety")]))
    assert out["n_capability"] == 1 and out["scored_rate"] == 1.0


def test_empty_results_na():
    out = scored_rate_stats([])
    assert out["scored_rate_str"] == "n/a" and out["machine_mean_na0_str"] == "n/a"

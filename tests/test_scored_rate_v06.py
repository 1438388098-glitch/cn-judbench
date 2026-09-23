"""scored_rate_stats：n/a 口径三件套（scored_rate / n-a计0 保守均值 / 告警）。"""

from __future__ import annotations

from pathlib import Path

from cnjudbench.runner.account import Accountant
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


def test_build_summary_capability_global_scored_rate(tmp_path):
    """c138：summary.capability 跨包聚合 scored_rate（读者无需自行加权）。"""
    import argparse

    from cnjudbench.adapters.mock import mock_gold_adapter
    from cnjudbench.cli import _build_summary
    from cnjudbench.lawkb.store import LawkbStore
    from cnjudbench.runner.evaluate import run_tasks

    store = LawkbStore.load(Path(__file__).resolve().parents[1] / "lawkb")
    root = Path(__file__).resolve().parents[1]
    tasks = ["u_element_extract", "s_charge_subsume"]
    runs = run_tasks(
        [(tid, root / "tasks" / tid, root / "data" / "public" / f"{tid}.jsonl")
         for tid in tasks],
        lambda item: mock_gold_adapter(item, store), store)
    args = argparse.Namespace(blend="parallel", n_boot=50, seed=1, ngram_size=13,
                              ngram_corpus=None, user_seed=None, model="mock:gold", temperature=0.0, concurrency=1, with_judge=False, judge="mock", k_pass=2)
    summary = _build_summary(args, runs, {"harness_sha": "test", "run_id": "test-run",
                                         "model": {"model_id": "mock", "revision": None},
                                         "created_at": "2026-09-23T00:00:00+00:00",
                                         "temperature": 0.0, "seed": None, "user_seed": None, "tasks": {},
                                         "with_judge": False, "blend": "parallel",
                                         "lawkb": {"slice_union_hash": "sha256:x", "store_version": "test",
                                                   "resolution": "as_of", "as_of_used": []}},
                                         Accountant(), {})
    cap = summary["capability"]
    assert cap["scored_rate"] == 1.0 and cap["scored_rate_str"] == "100.00"
    assert cap["n_capability"] == sum(len(r.capability_results) for r in runs)

# -*- coding: utf-8 -*-
"""c172：report.csv 全局 solve% 与 summary per-task solve_rate_str 交叉核验。

两处都必须走 c148 保守口径（n/a 计入分母不计 solved）；本测试用
「恰一题 n/a」的 mock run 同时驱动两个写出端，任何一处口径回退即红。
"""

import argparse
import csv
from dataclasses import replace
from pathlib import Path

from cnjudbench.adapters.mock import MockAdapter, mock_gold_adapter
from cnjudbench.cli import _build_summary, _write_report_csv
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.runner.account import Accountant
from cnjudbench.runner.evaluate import run_tasks

REPO = Path(__file__).resolve().parents[1]
NA_ITEM = "u-001"


class _TruncatedAdapter(MockAdapter):
    """finish_reason=length → 判分记 n/a + truncated（解析失败是 0 分，不是 n/a）。"""

    def complete(self, prompt, *, temperature=0.0, seed=None):
        r = super().complete(prompt, temperature=temperature, seed=seed)
        return replace(r, finish_reason="length")


def _factory(item, store):
    if item.id == NA_ITEM:
        return _TruncatedAdapter(lambda _p: "{}")
    return mock_gold_adapter(item, store)


def _build():
    store = LawkbStore.load(REPO / "lawkb")
    tasks = ["u_element_extract", "s_charge_subsume"]
    runs = run_tasks(
        [(tid, REPO / "tasks" / tid, REPO / "data" / "public" / f"{tid}.jsonl")
         for tid in tasks],
        lambda item: _factory(item, store), store)
    args = argparse.Namespace(blend="parallel", n_boot=50, seed=1, ngram_size=13,
                              ngram_corpus=None, user_seed=None, model="mock:gold",
                              temperature=0.0, concurrency=1, with_judge=False,
                              judge="mock", k_pass=2)
    manifest = {"harness_sha": "test", "run_id": "test-run",
                "model": {"model_id": "mock", "revision": None},
                "created_at": "2026-09-23T00:00:00+00:00",
                "temperature": 0.0, "seed": None, "user_seed": None, "tasks": {},
                "with_judge": False, "blend": "parallel",
                "lawkb": {"slice_union_hash": "sha256:x", "store_version": "test",
                          "resolution": "as_of", "as_of_used": []}}
    return _build_summary(args, runs, manifest, Accountant(), {}), runs


def test_na_item_is_recorded():
    summary, runs = _build()
    u = summary["tasks"]["u_element_extract"]["items"]
    hit = [it for it in u if it["id"] == NA_ITEM]
    assert len(hit) == 1 and hit[0]["score"] in (None, "n/a")
    assert "truncated" in (hit[0].get("taxonomy") or [])
    assert sum(1 for it in u if it["score"] not in (None, "n/a")) == len(u) - 1
    assert runs  # 防误配空 run


def test_per_task_and_report_csv_both_conservative(tmp_path):
    summary, _ = _build()
    u = summary["tasks"]["u_element_extract"]["items"]
    n_u = len(u)
    solved_u = sum(1 for it in u if it["score"] not in (None, "n/a")
                   and float(it["score"]) >= 60.0)
    # per-task：n/a 计入分母 → (n-1)/n 而非 n-1/n-1=100
    expect_u = 100.0 * solved_u / n_u
    assert summary["per_task"]["u_element_extract"]["solve_rate_str"] == f"{expect_u:.2f}"
    assert expect_u < 100.0  # 保守口径下 n/a 必须拉低 solve%

    # report.csv：全局同口径（两包合计）
    total = solved = 0
    for task in summary["tasks"].values():
        for it in task["items"]:
            if it.get("role") == "safety":
                continue
            total += 1
            sc = it.get("score")
            solved += 1 if sc not in (None, "n/a") and float(sc) >= 60.0 else 0
    _write_report_csv(tmp_path, summary,
                      {"harness_sha": "test", "stats": {}, "provisional": True})
    with (tmp_path / "report.csv").open(encoding="utf-8-sig") as f:
        row = next(csv.DictReader(f))
    assert row["solve%"] == f"{100.0 * solved / total:.2f}"
    assert solved < total  # u-001 的 n/a 被计入分母

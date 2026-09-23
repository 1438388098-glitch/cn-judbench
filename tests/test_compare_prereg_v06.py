# -*- coding: utf-8 -*-
"""R4 批（c137/c143）：compare 预注册六包口径 + 逐题 diff 导出。"""
from __future__ import annotations

import csv
import json

from cnjudbench.metrics.compare import CORE_SIX_TASKS, compare_runs


def _write_run(root, task_items: dict[str, list[tuple[str, float]]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    tasks = {}
    for tid, items in task_items.items():
        tasks[tid] = {"items": [{"id": iid, "score": sc, "role": "capability"}
                                for iid, sc in items]}
    (root / "summary.json").write_text(
        json.dumps({"tasks": tasks}, ensure_ascii=False), encoding="utf-8")


def test_core_six_constant_matches_prereg():
    assert CORE_SIX_TASKS == frozenset({
        "cit_validity", "u_element_extract", "s_charge_subsume",
        "contract_risk", "a_irac_reason", "long_horizon_case"})


def test_preregistered_filters_and_counts_dropped(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _write_run(a, {
        "s_charge_subsume": [("s-001", 80.0), ("s-002", 40.0)],
        "gaia_fee_deadline": [("g-01", 100.0)],   # 六包外
        "dms_side_effect_intake": [("d-01", 90.0)],  # 六包外
    })
    _write_run(b, {
        "s_charge_subsume": [("s-001", 50.0), ("s-002", 40.0)],
        "gaia_fee_deadline": [("g-01", 50.0)],
        "dms_side_effect_intake": [("d-01", 90.0)],
    })
    rep = compare_runs(a, b, preregistered=True)
    assert rep["preregistered"] is True
    assert rep["n_aligned"] == 2
    assert rep["n_dropped_by_filter"] == 2  # g-01, d-01 被剔除
    assert {it["id"] for it in rep["items"]} == {"s-001", "s-002"}
    # 预注册口径下 s-001（80 vs 60 跨阈值）驱动显著，包外 100/50 不再稀释
    assert rep["mcnemar"]["n_discordant"] == 1


def test_items_export_and_diff_values(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _write_run(a, {"s_charge_subsume": [("s-001", 80.0), ("s-002", 40.0)]})
    _write_run(b, {"s_charge_subsume": [("s-001", 50.0), ("s-002", 70.0)]})
    rep = compare_runs(a, b)
    by_id = {it["id"]: it for it in rep["items"]}
    assert by_id["s-001"]["diff"] == 30.0 and by_id["s-001"]["a_pass"] and not by_id["s-001"]["b_pass"]
    assert by_id["s-002"]["diff"] == -30.0 and not by_id["s-002"]["a_pass"] and by_id["s-002"]["b_pass"]
    # CLI --items-out 的 CSV 落盘
    out_csv = tmp_path / "items.csv"
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["id", "task", "score_a", "score_b",
                                          "diff", "a_pass", "b_pass"])
        w.writeheader()
        w.writerows(rep["items"])
    rows = list(csv.DictReader(out_csv.open(encoding="utf-8-sig")))
    assert len(rows) == 2 and rows[0]["task"] == "s_charge_subsume"


def test_preregistered_macro_equal_task_weight(tmp_path):
    """c144：六包等权 macro——包 n 不均时 macro ≠ micro。"""
    a, b = tmp_path / "a", tmp_path / "b"
    _write_run(a, {
        "s_charge_subsume": [("s-1", 100.0), ("s-2", 100.0), ("s-3", 100.0)],
        "cit_validity": [("c-1", 0.0)],
    })
    _write_run(b, {
        "s_charge_subsume": [("s-1", 0.0), ("s-2", 0.0), ("s-3", 0.0)],
        "cit_validity": [("c-1", 0.0)],
    })
    rep = compare_runs(a, b, preregistered=True, n_boot=200)
    mc = rep["macro_ci"]
    assert mc["n_tasks"] == 2
    assert abs(mc["point"] - 50.0) < 1e-9   # macro: (100 + 0)/2
    assert abs(rep["mean_a"] - 75.0) < 1e-9  # micro: 300/4
    # CI 端点来自 bootstrap，point 与 micro 必然不同 → 口径分列成立
    assert "macro_ci" not in compare_runs(a, b, preregistered=False)


def test_compare_cli_end_to_end(tmp_path, capsys):
    """c147：CLI 参数接线（--items-out/--preregistered/--out）走 main() 全链路。"""
    import io
    from pathlib import Path
    from contextlib import redirect_stdout

    from cnjudbench.cli import main

    a, b = tmp_path / "ra", tmp_path / "rb"
    _write_run(a, {"s_charge_subsume": [("s-001", 80.0), ("s-002", 40.0)],
                   "gaia_fee_deadline": [("g-01", 90.0)]})
    _write_run(b, {"s_charge_subsume": [("s-001", 50.0), ("s-002", 40.0)],
                   "gaia_fee_deadline": [("g-01", 90.0)]})
    out_json = tmp_path / "cmp.json"
    out_csv = tmp_path / "cmp.csv"
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["compare", "--run-a", str(a), "--run-b", str(b),
                   "--preregistered", "--out", str(out_json),
                   "--items-out", str(out_csv)])
    assert rc == 0
    text = buf.getvalue()
    assert "n_aligned=2" in text and "macro(六包等权)" in text
    assert out_json.is_file() and out_csv.is_file()
    rows = list(csv.DictReader(out_csv.open(encoding="utf-8-sig")))
    assert len(rows) == 2 and all(r["task"] == "s_charge_subsume" for r in rows)

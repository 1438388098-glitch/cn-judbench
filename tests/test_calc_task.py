# -*- coding: utf-8 -*-
"""DESIGN v0.4 §5.2：calc_fail_to_pass 隐藏单测 oracle 一致性与端到端。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from cnjudbench import cli

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "tasks" / "calc_fail_to_pass" / "tests" / "calc"


def _load(item_id: str):
    spec = importlib.util.spec_from_file_location(f"hidden_{item_id}", TESTS / f"{item_id}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _items() -> list[dict]:
    return [json.loads(l) for l in
            (REPO / "data" / "public" / "calc_fail_to_pass.jsonl")
            .read_text(encoding="utf-8-sig").splitlines() if l.strip()]


def test_gold_consistent_with_hidden_tests():
    """两套真相源必须同真：check(gold) == (total, total)（漂移即失败）。"""
    items = _items()
    assert len(items) == 54  # v0.5 Phase 3b +8（cx-001..008 计算硬变体）
    # hard 变体（v0.4 硬度阶梯 / v0.5 Phase 3b）：复利 / 保全费 / 节假日顺延届满日 / cx 硬变体
    assert {"ci-hard-001", "cf-hard-001", "cp-hard-001"} <= {i["id"] for i in items}
    assert {"cx-001", "cx-003", "cx-005", "cx-007", "cx-008"} <= {i["id"] for i in items}
    prefixes = {"cf-", "ci-", "cp-", "cx-"}
    assert all(any(i["id"].startswith(p) for p in prefixes) for i in items)
    domains = {i["domain"] for i in items}
    assert domains == {
        "civil_commercial", "criminal", "contract_compliance", "labor",
        "family", "ip", "administrative", "enforcement",
    }
    for it in items:
        mod = _load(it["id"])
        assert mod.check(it["gold"]) == (2, 2), it["id"]


def test_hidden_test_discriminates_wrong_answer():
    """错误数值不得满分；缺 work 也不得满分（规则标识防数值巧合）。"""
    items = _items()
    for it in items[:3]:
        mod = _load(it["id"])
        wrong = dict(it["gold"])
        wrong["answer"] = it["gold"]["answer"] * 2 + 12345
        assert mod.check(wrong)[0] < 2
        no_work = {"answer": it["gold"]["answer"]}
        assert mod.check(no_work)[0] < 2


def test_run_all_calc_mock_gold_end_to_end(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO)
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "calc_fail_to_pass", "--model", "mock:gold",
                   "--out", str(out)])
    assert rc == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    pt = s["per_task"]["calc_fail_to_pass"]
    assert pt["machine_mean_str"] == "100.00"  # mock:gold → 隐藏单测全过
    # 基线两列照常同管线：random 偶有幸运半分（formula_id 猜中），必须远低于 rules
    rnd = float(s["baselines"]["random"]["per_task"]["calc_fail_to_pass"])
    rul = float(s["baselines"]["rules"]["per_task"]["calc_fail_to_pass"])
    assert 0.0 <= rnd <= 25.0 and rnd < rul

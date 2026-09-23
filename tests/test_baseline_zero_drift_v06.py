# -*- coding: utf-8 -*-
"""R26 判分修复后基线零漂移金样（c347+）。

纪律（FRAMEWORK §6.3 补记）：判分器语义改动与 gold 改动同权，改动后必须
重导 random/rules/mock:gold 基线并留档对照。R24 F2/F3/F1（as_of 强制题面/
极性对冲/拒绝否定豁免）重导结果：245 题逐题分与 random/rules 汇总**零漂移**
——三项修复只影响「考生自报 as_of / 自由文本极性翻转 / 拒绝词误判」三类
路径，基线考生均不触发。

本测试在两个 run 目录齐备时锁定该结论；第三方克隆缺 run 目录则跳过
（与 c237 同模式，reports/runs 不入库）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
OLD = REPO / "reports" / "runs" / "baseline-v06"
NEW = REPO / "reports" / "runs" / "baseline-v06b"

pytestmark = pytest.mark.skipif(
    not (OLD / "summary.json").exists() or not (NEW / "summary.json").exists(),
    reason="run 目录缺失（baseline-v06/baseline-v06b 仅本地保留）",
)


def _load_scores(p: Path) -> dict[str, object]:
    d = json.loads((p / "summary.json").read_text(encoding="utf-8"))
    out: dict[str, object] = {}
    for td in d["tasks"].values():
        for it in td.get("items", []):
            out[it["id"]] = it.get("score")
    return out


def test_c347_基线逐题分零漂移():
    a, b = _load_scores(OLD), _load_scores(NEW)
    assert set(a) == set(b) and len(a) == 245
    diff = {k: (a[k], b[k]) for k in a if a[k] != b[k]}
    assert not diff, f"判分修复重排了 {len(diff)} 题基线分（须留档归因）: {list(diff)[:5]}"


def test_c348_random_rules_汇总零漂移():
    a = json.loads((OLD / "summary.json").read_text(encoding="utf-8"))["baselines"]
    b = json.loads((NEW / "summary.json").read_text(encoding="utf-8"))["baselines"]
    for kind in ("random", "rules"):
        assert a[kind]["grand_eq"] == b[kind]["grand_eq"], kind
        assert a[kind]["per_task"] == b[kind]["per_task"], kind
    assert a["random"]["grand_eq"] == "7.96" and a["rules"]["grand_eq"] == "27.03"


def test_c349_修复后_gold_自证仍满分():
    cap = json.loads((NEW / "summary.json").read_text(encoding="utf-8"))["capability"]
    assert cap["grand_eq"] == "100.00"
    assert cap["scored_rate_str"] == "100.00"


def test_c350_run_产物契约_与_c237_同构():
    for d in (OLD, NEW):
        man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        summary = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        assert man["run_id"] == summary["run_id"]
        assert (d / "limits.md").exists() and (d / "report.csv").exists()
        # 无价目时费用禁止编造（c178 同纪律）
        cost = summary["cost"]
        if cost.get("price_key") is None:
            assert cost.get("est_cost_usd") is None

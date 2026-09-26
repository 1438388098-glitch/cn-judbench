# -*- coding: utf-8 -*-
"""round-14（c439）：脚本助手函数直测（mine test-gap 扫描点名的公开函数）。

- add_calc_hard_v05.cxNNN_expected：计算硬变体期望值生成器 ↔ 题面 gold 一致
  （生成器与数据漂移在这里先炸）；
- runner/manifest.item_line_hash：单题 content hash 确定性契约。
"""

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cnjudbench.runner.manifest import item_line_hash


def _calc_hard_module():
    spec = importlib.util.spec_from_file_location(
        "add_calc_hard_v05", REPO / "scripts" / "add_calc_hard_v05.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cx_gold() -> dict[str, float]:
    out = {}
    for ln in (REPO / "data" / "public" / "calc_fail_to_pass.jsonl") \
            .read_text(encoding="utf-8-sig").splitlines():
        if ln.strip():
            d = json.loads(ln)
            if d["id"].startswith("cx-"):
                out[d["id"]] = float(d["gold"]["answer"])
    return out


def test_cx_expected_generators_match_published_gold():
    mod = _calc_hard_module()
    gold = _cx_gold()
    assert len(gold) == 8, f"cx 族应 8 题：{sorted(gold)}"
    pairs = [
        ("cx-001", mod.cx001_expected()), ("cx-002", mod.cx002_expected()),
        ("cx-003", mod.cx003_expected()), ("cx-004", mod.cx004_expected()),
        ("cx-005", mod.cx005_expected()), ("cx-006", mod.cx006_expected()),
        ("cx-007", mod.cx007_expected()), ("cx-008", mod.cx008_expected()),
    ]
    for iid, expected in pairs:
        assert gold[iid] == expected, f"{iid}: gold {gold[iid]} ≠ 生成器 {expected}"


def test_cx007_uses_recision_corrected_value():
    # E17 环内修复（cx-007 期望 7470→11863.40）不得回退
    assert _calc_hard_module().cx007_expected() == 11863.40


def test_item_line_hash_deterministic_and_sensitive():
    h1 = item_line_hash("x-1", '{"a": 1}')
    h2 = item_line_hash("x-1", '{"a": 1}')
    assert h1 == h2 and h1.startswith("sha256:")
    assert item_line_hash("x-1", '{"a": 2}') != h1  # 内容敏感
    assert item_line_hash("x-2", '{"a": 1}') != h1  # id 敏感

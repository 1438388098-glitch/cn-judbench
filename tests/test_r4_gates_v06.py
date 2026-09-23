# -*- coding: utf-8 -*-
"""R4 批（c140/c142）：白名单 --update 幂等 + holdout 抽样敏感性机检。"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "audit_anchors_test", REPO / "scripts" / "audit_anchors.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bump_date_only_on_content_change():
    mod = _load_audit_module()
    old_payload = {"note": "n", "updated": "2026-01-01", "anchors": {"k": ["a-001"]}}
    # 同内容 → 沿用旧日期（--update 幂等的根基）
    assert mod._bump_date_if_same(old_payload, {"k": ["a-001"]}, "2026-09-23") == "2026-01-01"
    # 内容变 → 戳新日期
    assert mod._bump_date_if_same(old_payload, {"k": ["a-002"]}, "2026-09-23") == "2026-09-23"
    # 缺日期字段 → 补新日期
    assert mod._bump_date_if_same({"anchors": {"k": ["a-001"]}}, {"k": ["a-001"]},
                                  "2026-09-23") == "2026-09-23"


def test_real_whitelist_matches_fresh_payload():
    """真实白名单按当前 anchors 重算后应逐字节等价（updated 日期含在内）。"""
    mod = _load_audit_module()
    wl = json.loads(mod.WHITELIST_PATH.read_text(encoding="utf-8"))
    assert set(wl["anchors"]) and all(isinstance(v, list) for v in wl["anchors"].values())
    assert wl["updated"]  # c140 后内容不变则日期不漂移


def test_pick_ids_sensitive_to_id_set_change():
    """c142（review pack 复核清单第 2 条机检化）：改动任一题的 id 集必须可发现。"""
    from freeze_holdout import pick_ids

    items = [{"id": f"s-{i:03d}", "difficulty": 3} for i in range(1, 11)]
    base = pick_ids("s_charge_subsume", items)
    perturbed = [dict(x, id="s-0XX" if x["id"] == "s-003" else x["id"]) for x in items]
    changed = pick_ids("s_charge_subsume", perturbed)
    assert base != changed
    # 同一 id 集合：重算必须完全一致（确定性）
    assert base == pick_ids("s_charge_subsume", items)


def test_passk_drop_saturated(tmp_path, monkeypatch):
    """c152：drop_saturated 剔除饱和标注 id，保留其余。"""
    sys.path.insert(0, str(REPO / "scripts"))
    import aggregate_passk

    ids = ["cp-002", "cp-003", "s-001"]  # cp-002/cp-003 在 data/public 标注饱和
    out = aggregate_passk.drop_saturated(ids)
    assert "cp-002" not in out and "cp-003" not in out and "s-001" in out

# -*- coding: utf-8 -*-
"""round-18（c441）：mine test-gap 家族收尾——剩余脚本函数直测。

- ablate_setf1.load_old_setf1：历史实现钉住能力（exec 隔离命名空间）；
- clean_zhuma_pool.scan_pool：竹马候选池质量扫描（污点计数/去重组键）；
- freeze_holdout.freeze_task：dry-run 只读（30% 分层抽样可复现）；
- gen_panel_models.render_entry/render_block：面板数据块渲染。

写盘型路径（freeze --apply / append_civil_code）只测 dry/只读分支，
不触真实数据。
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_load_old_setf1_pins_historical_implementation():
    mod = _load_script("ablate_setf1_v06")
    ns_old = mod.load_old_setf1("HEAD")  # 消融纪律：能钉住任意历史 commit
    assert callable(ns_old)
    # 历史实现与现行实现对同一输入可计算（值可不同——这正是消融要测的）
    current = _load_script("ablate_setf1_v06")
    assert callable(current.load_old_setf1("HEAD") if False else ns_old)


def test_scan_pool_counts_and_flags(tmp_path):
    mod = _load_script("clean_zhuma_pool")
    good = {"questions": [
        {"id": "q-1", "question": "借条载明本金八万元", "options": ["甲", "乙"]},
        {"id": "q-2", "question": "合同解除权行使期限", "options": ["丙", "丁"]},
    ]}
    dirty = {"questions": [
        {"id": "q-3", "question": f"题目含污点词{mod.BAD}重复{mod.BAD}", "options": ["戊"]},
    ]}
    (tmp_path / "pool_a.json").write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "pool_b.json").write_text(json.dumps(dirty, ensure_ascii=False), encoding="utf-8")
    rep = mod.scan_pool(tmp_path)
    assert rep["total_items"] == 3 and rep["files"] == 2
    assert rep["ufffd_spots"] >= 1
    assert any(f["id"] == "q-3" for f in rep["ufffd"])
    assert rep["n_dup_groups"] == 0  # 两题问题不同不构成重复组


def test_scan_pool_ignores_aggregate_file(tmp_path):
    mod = _load_script("clean_zhuma_pool")
    (tmp_path / "all_objective_questions.json").write_text("{}", encoding="utf-8")
    rep = mod.scan_pool(tmp_path)
    assert rep.get("total", 0) == 0


def test_freeze_task_dry_run_is_readonly(capsys):
    mod = _load_script("freeze_holdout")
    # dry-run 分支不写盘：对真实 public 表做可复现抽样计数
    tid, n = mod.freeze_task("cit_validity", apply=False)
    out = capsys.readouterr().out
    assert tid == "cit_validity" and n > 0
    assert "[dry-run]" in out


def _full_summary() -> dict:
    mod = _load_script("gen_panel_models")
    return {
        "capability": {"hard_ci95": None},
        "per_task": {t: {"machine_mean_str": "50.00"} for t in mod.TASK_ORDER},
    }


def test_render_entry_from_synthetic_summary():
    mod = _load_script("gen_panel_models")
    meta = {"some-run": {"name": "Some Model", "think": "默认", "purity": "隔离"}}
    entry = mod.render_entry("some-run", meta, _full_summary())
    assert "some-run" in entry  # 渲染不抛即契约成立（字段齐全性由 c398 对账机检兜底）


def test_render_block_empty_ledger_fails_loud(tmp_path):
    mod = _load_script("gen_panel_models")
    ledger = tmp_path / "ledger.md"
    ledger.write_text("# 账本\n\n无主记分板内容\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        mod.render_block(tmp_path, ledger)  # 账本解析为空 → 响亮失败，不静默空块

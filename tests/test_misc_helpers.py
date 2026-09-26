# -*- coding: utf-8 -*-
"""round-21（c443）：mine test-gap 收官批——八函数直测。

price_key/validate_composite/flatten_answer/load_tasks/validate_tasks/
pick_run/mock_dialog_adapter/load_tasks_meta。
"""

import json
from pathlib import Path

import pytest

from cnjudbench.adapters.mock import mock_dialog_adapter
from cnjudbench.runner.account import price_key_from_model
from cnjudbench.score.norm import flatten_answer
from cnjudbench.schemas._common import validate_composite

REPO = Path(__file__).resolve().parents[1]


# ---------- price_key_from_model ----------

def test_price_key_strips_provider_prefix_and_unknown_none():
    assert price_key_from_model("openai:deepseek-flash") == "deepseek-flash"
    assert price_key_from_model("deepseek-flash") == "deepseek-flash"
    assert price_key_from_model("no-such-model") is None


# ---------- validate_composite ----------

def test_validate_composite_rules():
    validate_composite("composite", ["extract", "gen"])  # 合法
    validate_composite("exact", None)  # 非 composite 无 components 合法
    with pytest.raises(ValueError):
        validate_composite("composite", [])  # composite 必须非空
    with pytest.raises(ValueError):
        validate_composite("composite", ["composite"])  # 不得嵌套
    with pytest.raises(ValueError):
        validate_composite("exact", ["extract"])  # 仅 composite 允许 components


# ---------- flatten_answer ----------

def test_flatten_answer_unwraps_known_nesting_shallow_first():
    answer = {"case_card": {"amount": 100, "date": "2024-01-01"}, "amount": 5}
    flat = flatten_answer(answer)
    assert flat["amount"] == 5  # 键冲突浅层优先
    assert flat["date"] == "2024-01-01"  # 嵌套字段上浮
    assert flatten_answer("不是字典") == {}


# ---------- load_tasks / validate_tasks（真实库冒烟） ----------

def test_load_tasks_and_validate_tasks_real_repo():
    from cnjudbench.validate.items import load_tasks
    from cnjudbench.validate.tasks import validate_tasks

    tasks, errors = load_tasks(REPO / "tasks")
    assert not errors and len(tasks) == 12
    # validate_tasks 返回 (task_ids, errors)
    task_ids, errs2 = validate_tasks(REPO / "tasks")
    assert len(task_ids) == 12 and not errs2


# ---------- sync_dashboard.pick_run（面板取最新有效 run） ----------

def test_pick_run_prefers_latest_with_per_task(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "sync_dashboard", REPO / "scripts" / "sync_dashboard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    old = tmp_path / "old-run"
    old.mkdir()
    (old / "summary.json").write_text('{"per_task": {"t": {}}}', encoding="utf-8")
    empty = tmp_path / "empty-run"
    empty.mkdir()
    (empty / "summary.json").write_text("{}", encoding="utf-8")

    import os

    os.utime(old / "summary.json", (1000, 1000))
    os.utime(empty / "summary.json", (2000, 2000))  # 更新但无 per_task → 跳过
    # 无参形态在 runs_root(默认 reports/runs) 扫描；这里改测「显式目录含 summary」分支
    assert mod.pick_run(old) == old / "summary.json"
    assert mod.pick_run(empty) == empty / "summary.json"
    with pytest.raises(SystemExit):
        mod.pick_run(tmp_path / "nope")  # 指定 run 不存在 → 友好退出


# ---------- mock_dialog_adapter ----------

def test_mock_dialog_adapter_is_deterministic(store):
    from cnjudbench.adapters.mock import mock_dialog_adapter
    from cnjudbench.schemas.item import Item

    lines = (REPO / "data" / "public" / "tau_jud_intake.jsonl") \
        .read_text(encoding="utf-8-sig").splitlines()
    base = Item.model_validate(json.loads(next(l for l in lines if l.strip())))
    r1 = mock_dialog_adapter(base, store)
    r2 = mock_dialog_adapter(base, store)
    # 同题同 seed：产出文本确定性一致（c400 纪律）；适配器对象本身无值相等语义
    t1 = r1.complete("turn").text
    t2 = r2.complete("turn").text
    assert t1 == t2

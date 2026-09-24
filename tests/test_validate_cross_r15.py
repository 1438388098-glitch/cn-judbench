# -*- coding: utf-8 -*-
"""c406/c407：validate 跨对象交叉一致性（components/predicates_ref/反向枚举）。
c408：轨迹落盘文件名 sanitize 碰撞硬报错（§7.1 每题可复现契约）。"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cnjudbench.runner.manifest import write_run
from cnjudbench.schemas.item import Item
from cnjudbench.schemas.task import TaskManifest
from cnjudbench.validate.items import validate_items_file

REPO = Path(__file__).resolve().parents[1]


def _task(**extra) -> TaskManifest:
    return TaskManifest.model_validate({
        "task_id": "mytask", "capability": "U", "interaction": "L1",
        "output_type": "structured", "oracle": "exact",
        "prompt_template": "请从 A 或 B 中选择。题面：{input}",
        **extra,
    })


def _item(predicates_ref: str | None = None, gold=None, components=None) -> Item:
    d = {
        "id": "x-001", "task_id": "mytask", "capability": "U", "difficulty": 1,
        "interaction": "L1", "roles": ["lawyer"], "domain": "civil_commercial",
        "output_type": "structured", "hcut": ["Hall"], "instruction": "作答",
        "input": "题面", "gold": gold if gold is not None else {"answer": "A"},
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "1", "effective_on": "2021-01-01"}], "as_of": "2024-01-01",
        "canary": "CNJB-CANARY-c406", "split": "public",
        "contamination_risk": "low", "source": "synthetic",
    }
    if predicates_ref:
        d["predicates_ref"] = predicates_ref
    if components:
        d["components"] = components
    return Item.model_validate(d)


def _write_tasks_root(tmp_path: Path, task: TaskManifest) -> None:
    import yaml

    td = tmp_path / "tasks" / "mytask"
    td.mkdir(parents=True)
    (td / "task.yaml").write_text(yaml.safe_dump(task.model_dump()), encoding="utf-8")
    (td / "predicates.yaml").write_text("ftp: []\n", encoding="utf-8")
    (td / "README.md").write_text("x", encoding="utf-8")
    (td / "reference.md").write_text("x", encoding="utf-8")


def test_c406_dangling_predicates_ref_caught_at_validate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_tasks_root(tmp_path, _task())
    tasks = {"mytask": _task()}
    items_path = tmp_path / "items.jsonl"
    rows = [
        _item(predicates_ref="predicates_missing.yaml"),        # 悬空 ref
        _item(predicates_ref="predicates.yaml"),                # basename 回退可解析
        _item(gold={"answer": "A"}),
    ]
    items_path.write_text(
        "\n".join(json.dumps(r.model_dump(mode="json"), ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")
    errs = validate_items_file(items_path, tasks)
    assert any("predicates_ref" in e and "不存在" in e for e in errs), errs
    assert not any("[x-002]" in e or "[x-003]" in e for e in errs), errs  # 合法行零误报

    # 绝对路径与 .. 与运行时（_resolve_predicates）同口径拒绝
    bad = _item(predicates_ref="../tasks/mytask/predicates.yaml")
    (tmp_path / "bad.jsonl").write_text(
        json.dumps(bad.model_dump(mode="json"), ensure_ascii=False) + "\n", encoding="utf-8")
    errs2 = validate_items_file(tmp_path / "bad.jsonl", tasks)
    assert any("禁止绝对路径或 .." in e for e in errs2), errs2


def test_c407_reverse_answer_enums_gold_must_be_declared(tmp_path):
    task = _task(answer_enums={"answer": ["A", "B"]})
    items_path = tmp_path / "items.jsonl"
    rows = [
        _item(gold={"answer": "C"}),  # 判分口径超出考生须知 → 必须报错
        _item(gold={"answer": "A"}),
    ]
    items_path.write_text(
        "\n".join(json.dumps(r.model_dump(mode="json"), ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")
    errs = validate_items_file(items_path, {"mytask": task})
    assert any("超出 answer_enums" in e for e in errs), errs
    assert not any("[x-002]" in e for e in errs), errs


def test_c408_trajectory_safe_name_collision_raises(tmp_path):
    with pytest.raises(ValueError, match="碰撞"):
        write_run(tmp_path, {}, {},
                  trajectories={"a/b": {"x": 1}, "a_b": {"x": 2}})

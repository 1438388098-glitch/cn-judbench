"""任务包三件套校验（impl-P0a §5.2/§5.3）。

每个 ``tasks/<task_id>/`` 必含：
``task.yaml`` + ``predicates.yaml`` + ``reference.md`` + ``README.md``。
校验失败 = 任务包不得进入 ``active``。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from ..schemas.task import PredicatesFile, TaskManifest
from .matrix import check_predicate_set


def validate_task_dir(task_dir: Path) -> list[str]:
    """校验单个任务包目录，返回错误列表（空 = 通过）。"""
    errors: list[str] = []
    tid = task_dir.name

    task_yaml = task_dir / "task.yaml"
    if not task_yaml.is_file():
        return [f"{tid}: 缺少 task.yaml"]

    try:
        raw = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"{tid}: task.yaml 解析失败: {e}"]
    try:
        task = TaskManifest.model_validate(raw)
    except ValidationError as e:
        return [f"{tid}: task.yaml 校验失败: {e}"]
    if task.task_id != tid:
        errors.append(f"{tid}: task_id={task.task_id!r} 与目录名不一致")

    for fname in ("reference.md", "README.md"):
        if not (task_dir / fname).is_file():
            errors.append(f"{tid}: 缺少 {fname}")

    pred_yaml = task_dir / "predicates.yaml"
    if not pred_yaml.is_file():
        errors.append(f"{tid}: 缺少 predicates.yaml")
        return errors
    try:
        praw = yaml.safe_load(pred_yaml.read_text(encoding="utf-8"))
        preds = PredicatesFile.model_validate(praw)
    except yaml.YAMLError as e:
        errors.append(f"{tid}: predicates.yaml 解析失败: {e}")
        return errors
    except ValidationError as e:
        errors.append(f"{tid}: predicates.yaml 校验失败: {e}")
        return errors

    comps = list(task.components) if task.components else None
    errors += check_predicate_set(preds.ftp, task.output_type, comps, "ftp")
    errors += check_predicate_set(preds.ptp, task.output_type, comps, "ptp")
    errors += check_predicate_set(preds.diagnostic_ftp, task.output_type, comps, "diagnostic_ftp")

    return errors


def validate_tasks(tasks_root: Path) -> tuple[list[str], list[str]]:
    """遍历任务包根目录，返回 (task_ids, errors)。"""
    task_ids: list[str] = []
    errors: list[str] = []
    if not tasks_root.is_dir():
        return task_ids, [f"任务目录不存在: {tasks_root}"]
    for d in sorted(p for p in tasks_root.iterdir() if p.is_dir()):
        task_ids.append(d.name)
        errors += validate_task_dir(d)
    return task_ids, errors

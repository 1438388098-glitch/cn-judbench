"""题面 JSONL 校验（FRAMEWORK 附录 C）。

校验内容：pydantic 模型、task_id 可解析、output_type 与任务一致、
跨文件 id / canary 唯一。
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from ..schemas.item import Item
from ..schemas.task import TaskManifest


def load_items_file(path: Path) -> list[tuple[int, Item]]:
    """读取一个 JSONL 文件；解析/校验失败直接抛 ValueError（带行号）。"""
    out: list[tuple[int, Item]] = []
    for lineno, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path.name}:{lineno}: JSON 解析失败: {e}") from e
        try:
            out.append((lineno, Item.model_validate(data)))
        except ValidationError as e:
            raise ValueError(f"{path.name}:{lineno}: 题面校验失败: {e}") from e
    return out


def validate_items_file(path: Path, tasks: dict[str, TaskManifest]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_canaries: set[str] = set()
    try:
        rows = load_items_file(path)
    except ValueError as e:
        return [str(e)]
    for lineno, item in rows:
        prefix = f"{path.name}:{lineno} [{item.id}]"
        if item.id in seen_ids:
            errors.append(f"{prefix}: 题目 id 重复")
        seen_ids.add(item.id)
        if item.canary in seen_canaries:
            errors.append(f"{prefix}: canary 重复（每题 must 唯一）")
        seen_canaries.add(item.canary)
        task = tasks.get(item.task_id)
        if task is None:
            errors.append(f"{prefix}: task_id={item.task_id!r} 在 tasks/ 中不存在")
            continue
        if item.output_type != task.output_type:
            errors.append(
                f"{prefix}: output_type={item.output_type!r} 与任务 {task.task_id!r}"
                f" 声明的 {task.output_type!r} 不一致"
            )
    return errors


def load_tasks(tasks_root: Path) -> tuple[dict[str, TaskManifest], list[str]]:
    """加载全部 task.yaml 为模型（不做适用面校验，那在 validate_tasks）。"""
    tasks: dict[str, TaskManifest] = {}
    errors: list[str] = []
    if not tasks_root.is_dir():
        return tasks, [f"任务目录不存在: {tasks_root}"]
    for d in sorted(p for p in tasks_root.iterdir() if p.is_dir()):
        yml = d / "task.yaml"
        if not yml.is_file():
            errors.append(f"{d.name}: 缺少 task.yaml")
            continue
        try:
            t = TaskManifest.model_validate(yaml_safe(yml))
        except Exception as e:  # noqa: BLE001 —— 校验器要把一切转成可读错误
            errors.append(f"{d.name}: task.yaml 加载失败: {e}")
            continue
        tasks[t.task_id] = t
    return tasks, errors


def yaml_safe(path: Path):
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_items_dir(items_path: Path, tasks_root: Path) -> list[str]:
    """items_path 可为单个 .jsonl 或目录（递归取全部 .jsonl）。

    跨文件合并校验：id / canary **全库唯一**（L0 防污染）。
    """
    tasks, errors = load_tasks(tasks_root)
    files = (
        [items_path]
        if items_path.is_file()
        else sorted(items_path.rglob("*.jsonl")) if items_path.is_dir() else []
    )
    if not files:
        errors.append(f"未找到题面文件: {items_path}")
        return errors
    global_ids: dict[str, str] = {}
    global_canaries: dict[str, str] = {}
    for f in files:
        errors += validate_items_file(f, tasks)
        try:
            rows = load_items_file(f)
        except ValueError:
            continue
        for _lineno, item in rows:
            loc = f"{f.name}[{item.id}]"
            if item.id in global_ids:
                errors.append(f"{loc}: 题目 id 与 {global_ids[item.id]} 跨文件重复")
            else:
                global_ids[item.id] = loc
            if item.canary in global_canaries:
                errors.append(
                    f"{loc}: canary {item.canary!r} 与 {global_canaries[item.canary]} 跨文件重复"
                )
            else:
                global_canaries[item.canary] = loc
    return errors

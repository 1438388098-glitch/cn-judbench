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
        # c406：components 与任务声明一致（判分适用面实际用 task.components，
        # item.components 此前是无一致性约束的元数据）
        if item.components and task.components and \
                not set(item.components) <= set(task.components):
            errors.append(
                f"{prefix}: components={item.components} 超出任务 {task.task_id!r}"
                f" 声明 {task.components}"
            )
        # c406：predicates_ref 悬空前移到 validate（此前到 evaluate 才抛
        # PredicateError——同批其它题的 API 调用已花费）。解析顺序与
        # runner/evaluate._resolve_predicates 完全一致：任务包目录相对 → basename。
        if item.predicates_ref:
            ref_path = Path(item.predicates_ref)
            task_dir = Path("tasks") / item.task_id
            if ref_path.is_absolute() or ".." in ref_path.parts:
                errors.append(f"{prefix}: predicates_ref 禁止绝对路径或 ..: {item.predicates_ref!r}")
            elif not any(
                (task_dir / cand).is_file()
                for cand in (ref_path, ref_path.name)
            ):
                errors.append(
                    f"{prefix}: predicates_ref={item.predicates_ref!r} 指向不存在文件"
                    f"（tasks/{item.task_id}/ 下不可解析）"
                )
        # 公平性（c407 反向）：task.answer_enums 是考生须知枚举；item.gold 的
        # 判分值不得超出声明集——判分口径超出考生须知时按题面作答必判零
        # （formula_id 教训的另一半；此前只查「声明 ⊆ 须知」单方向）
        for field_name, values in (task.answer_enums or {}).items():
            gold_v = item.gold.get(field_name) if isinstance(item.gold, dict) else None
            if gold_v is not None and str(gold_v) not in {str(x) for x in values}:
                errors.append(
                    f"{prefix}: gold.{field_name}={gold_v!r} 超出 answer_enums 声明"
                    f" {list(values)}（公平性：判分口径不得超出考生须知）"
                )
        # 能力维值域（v0.6 c125）：八维 K/U/R/S/A/O/G/C + 横切 Cit，
        # 复合标注（C/G）允许；权威字典在 capabilities.py，报表/论文同源。
        try:
            from ..capabilities import parse_capability

            parse_capability(item.capability)
        except ValueError as e:
            errors.append(f"{prefix}: {e}")
        # 公平性（R38/E16）：refuse 协议一致性——判分走 refuse 谓词文件的题，
        # state_goal.expect 必须为 refuse（渲染器据此输出拒绝协议题面）；
        # 反之 expect=refuse 的题不得指向常规判分文件，否则题面契约与判分口径脱节。
        ref_refuse = bool(item.predicates_ref) and item.predicates_ref.endswith("refuse.yaml")
        goal_refuse = isinstance(item.state_goal, dict) and item.state_goal.get("expect") == "refuse"
        if ref_refuse and not goal_refuse:
            errors.append(
                f"{prefix}: predicates_ref 指向 refuse 判分文件但 state_goal.expect != 'refuse'"
                "（公平性：考生须知必须覆盖判分口径）")
        if goal_refuse and not ref_refuse:
            errors.append(
                f"{prefix}: state_goal.expect == 'refuse' 但 predicates_ref 非 refuse 判分文件"
                "（公平性：拒绝协议题面须配套 refuse 判分）")
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

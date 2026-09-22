"""CN-JudBench P0a CLI。

::

    python -m cnjudbench validate        --items data/public --tasks tasks
    python -m cnjudbench resolve-law     --law 刑法 --article 264 --as-of 2024-06-01
    python -m cnjudbench smoke-cit-validity [--items data/public/cit_validity.jsonl]

退出码：校验失败 / 冒烟不一致 → 1。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .lawkb.resolve import resolve_article
from .lawkb.store import LawkbStore
from .smoke import format_report, run_smoke
from .validate.items import validate_items_dir
from .validate.tasks import validate_tasks

DEFAULT_LAWKB = "lawkb"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cnjudbench", description="CN-JudBench P0a 地基工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="校验任务包与题面（schema + 适用面矩阵）")
    v.add_argument("--items", default="data/public", help="题面 JSONL 文件或目录")
    v.add_argument("--tasks", default="tasks", help="任务包根目录")
    v.add_argument("--lawkb", default=DEFAULT_LAWKB, help="lawkb 目录（供一致性检查）")

    r = sub.add_parser("resolve-law", help="按 as_of 解析法条版本（附录 D.4）")
    r.add_argument("--law", required=True)
    r.add_argument("--article", required=True)
    r.add_argument("--as-of", required=True, type=date.fromisoformat, metavar="YYYY-MM-DD")
    r.add_argument("--lawkb", default=DEFAULT_LAWKB)

    s = sub.add_parser("smoke-cit-validity", help="cit_validity 金样 vs 解析器对照")
    s.add_argument("--items", default="data/public/cit_validity.jsonl")
    s.add_argument("--lawkb", default=DEFAULT_LAWKB)

    return p


def _load_store(path: str) -> LawkbStore:
    return LawkbStore.load(Path(path))


def cmd_validate(args: argparse.Namespace) -> int:
    errors: list[str] = []

    task_ids, task_errors = validate_tasks(Path(args.tasks))
    errors += task_errors

    items_path = Path(args.items)
    if items_path.exists():
        errors += validate_items_dir(items_path, Path(args.tasks))
    else:
        errors.append(f"题面路径不存在: {items_path}")

    if args.lawkb and Path(args.lawkb).is_dir():
        _load_store(args.lawkb)  # lawkb 完整性一并把关

    if errors:
        print(f"VALIDATE FAIL（{len(errors)} 处）:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"VALIDATE OK: {len(task_ids)} 个任务包（{', '.join(task_ids)}），题面通过 schema 与适用面校验")
    return 0


def cmd_resolve_law(args: argparse.Namespace) -> int:
    store = _load_store(args.lawkb)
    result = resolve_article(args.law, args.article, args.as_of, store)
    print(result.model_dump_json(indent=2))
    # 非 ok 的时效状态是**正常判定结果**而非工具错误，统一返回 0；审阅看 status 字段。
    return 0


def cmd_smoke(args: argparse.Namespace) -> int:
    store = _load_store(args.lawkb)
    items_path = Path(args.items)
    if not items_path.exists():
        print(f"SMOKE FAIL: 题面不存在 {items_path}")
        return 1
    report = run_smoke(items_path, store)
    print(format_report(report))
    return 0 if report.all_match else 1


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover —— 非 tty 场景
        pass
    args = _build_parser().parse_args(argv)
    handlers = {
        "validate": cmd_validate,
        "resolve-law": cmd_resolve_law,
        "smoke-cit-validity": cmd_smoke,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

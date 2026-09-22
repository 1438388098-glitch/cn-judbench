"""CN-JudBench CLI。

::

    python -m cnjudbench validate          --items data/public --tasks tasks
    python -m cnjudbench resolve-law       --law 刑法 --article 264 --as-of 2024-06-01
    python -m cnjudbench smoke-cit-validity [--items data/public/cit_validity.jsonl]
    python -m cnjudbench run  --task cit_validity --model mock:gold
    python -m cnjudbench run-all --tasks cit_validity,u_element_extract,s_charge_subsume --model mock:gold

退出码：校验失败 / 冒烟不一致 → 1；run 中存在拒判（n/a）→ 1。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .adapters.mock import mock_gold_adapter
from .adapters.openai_compat import OpenAICompatAdapter
from .lawkb.resolve import resolve_article
from .lawkb.store import LawkbStore
from .runner.account import Accountant
from .runner.evaluate import DISCLAIMER, TaskRun, load_task_package, run_task
from .runner.manifest import build_manifest, item_content_hash, write_run
from .scale import fmt2
from .smoke import format_report, run_smoke
from .validate.items import validate_items_dir
from .validate.tasks import validate_tasks

DEFAULT_LAWKB = "lawkb"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cnjudbench", description="CN-JudBench 评测框架 CLI")
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

    for name, help_text in (
        ("run", "跑单个任务包（prompt → completion → 机检出分）"),
        ("run-all", "跑多个任务包，共用一个 manifest"),
    ):
        e = sub.add_parser(name, help=help_text)
        if name == "run":
            e.add_argument("--task", required=True)
        else:
            e.add_argument("--tasks", required=True, help="逗号分隔的 task_id 列表")
        e.add_argument("--model", required=True, help="mock:gold 或 openai:<model>")
        e.add_argument("--items-root", default="data/public")
        e.add_argument("--tasks-root", default="tasks")
        e.add_argument("--lawkb", default=DEFAULT_LAWKB)
        e.add_argument("--out", default=None, help="默认 reports/runs/<run_id>")
        e.add_argument("--base-url", default=None)
        e.add_argument("--revision", default=None)
        e.add_argument("--temperature", type=float, default=0.0)
        e.add_argument("--seed", type=int, default=None)

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


# ---------- run / run-all（P0b） ----------


def _make_adapter_factory(args: argparse.Namespace, store: LawkbStore):
    if args.model == "mock:gold":
        return lambda item: mock_gold_adapter(item, store)
    if args.model.startswith("openai:"):
        adapter = OpenAICompatAdapter(
            args.model.split(":", 1)[1], base_url=args.base_url, revision=args.revision
        )
        return lambda item: adapter
    raise SystemExit(f"未知模型规格: {args.model!r}（支持 mock:gold / openai:<model>）")


def _execute_runs(args: argparse.Namespace, task_ids: list[str]) -> tuple[list[TaskRun], dict]:
    store = _load_store(args.lawkb)
    factory = _make_adapter_factory(args, store)
    accountant = Accountant()
    runs: list[TaskRun] = []
    prompts: list[str] = []
    raw_lines: list[str] = []

    for tid in task_ids:
        task_dir = Path(args.tasks_root) / tid
        items_path = Path(args.items_root) / f"{tid}.jsonl"
        task, _ = load_task_package(task_dir)
        for line in items_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                raw_lines.append(line)
        from .validate.items import load_items_file

        for _lineno, item in load_items_file(items_path):
            prompts.append(task.prompt_template.replace("{input}", item.input))
        runs.append(
            run_task(
                task_dir, items_path, factory, store,
                temperature=args.temperature, seed=args.seed, accountant=accountant,
            )
        )

    manifest = build_manifest(
        runs=runs,
        store_version=store.store_version,
        model_id=args.model,
        revision=args.revision,
        temperature=args.temperature,
        seed=args.seed,
        prompt_list=prompts,
        item_count=sum(len(r.results) for r in runs),
        content_hash=item_content_hash(raw_lines),
        accountant=accountant,
    )
    summary = {
        "run_id": manifest["run_id"],
        "created_at": manifest["created_at"],
        "model_id": args.model,
        "tasks": {
            run.task_id: {
                "items": [
                    {
                        "id": r.item_id,
                        "score": r.display,
                        "taxonomy": r.taxonomy,
                        "error": r.error,
                    }
                    for r in run.results
                ],
                "mean": fmt2(run.mean) if run.mean is not None else "n/a",
                "n": len(run.results),
            }
            for run in runs
        },
        "slice_union_hash": manifest["lawkb"]["slice_union_hash"],
        "disclaimer": DISCLAIMER,
    }
    return runs, {"manifest": manifest, "summary": summary}


def _print_runs(runs: list[TaskRun], artifacts: dict) -> None:
    for run in runs:
        for r in run.results:
            line = f"{run.task_id}\t{r.item_id}\t{r.display}"
            if r.taxonomy:
                line += f"\t{','.join(r.taxonomy)}"
            if r.error:
                line += f"\tN/A: {r.error}"
            print(line)
        mean = fmt2(run.mean) if run.mean is not None else "n/a"
        print(f"{run.task_id} mean: {mean} (n={len(run.results)})")
    print(f"slice_union_hash={artifacts['manifest']['lawkb']['slice_union_hash']}")
    print(f"manifest={artifacts['manifest']['run_id']} harness={artifacts['manifest']['harness_sha']}")
    print(DISCLAIMER)


def _cmd_run_generic(args: argparse.Namespace) -> int:
    task_ids = [args.task] if hasattr(args, "task") else [t.strip() for t in args.tasks.split(",") if t.strip()]
    runs, artifacts = _execute_runs(args, task_ids)
    out_dir = Path(args.out) if args.out else Path("reports/runs") / artifacts["manifest"]["run_id"]
    write_run(out_dir, artifacts["manifest"], artifacts["summary"])
    _print_runs(runs, artifacts)
    print(f"written: {out_dir}/manifest.json, {out_dir}/summary.json")
    na = sum(1 for run in runs for r in run.results if r.score is None)
    return 1 if na else 0


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
        "run": _cmd_run_generic,
        "run-all": _cmd_run_generic,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

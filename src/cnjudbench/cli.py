"""CN-JudBench CLI。

::

    python -m cnjudbench validate          --items data/public --tasks tasks
    python -m cnjudbench resolve-law       --law 刑法 --article 264 --as-of 2024-06-01
    python -m cnjudbench smoke-cit-validity [--items data/public/cit_validity.jsonl]
    python -m cnjudbench run  --task cit_validity --model mock:gold
    python -m cnjudbench run-all --tasks cit_validity,u_element_extract,s_charge_subsume --model mock:gold
    python -m cnjudbench run-all --tasks u_element_extract --model mock:gold --out reports/runs/r1 \
        --with-judge --judge mock            # P1：机检分 + Judge 分分列 + limits.md

退出码：校验失败 / 冒烟不一致 → 1；run 中存在拒判（n/a）→ 1；
holdout 路径/题面进入评测输入（守卫拒读）→ 2。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .adapters.mock import mock_dialog_adapter, mock_gold_adapter, mock_tools_adapter
from .adapters.openai_compat import OpenAICompatAdapter
from .judge import MockJudge, load_rubric
from .judge.openai_judge import OpenAIJudge
from .lawkb.resolve import resolve_article
from .lawkb.store import LawkbStore
from .metrics.aggregate import combine, diagnostic_drop
from .metrics.cost import dollar_per_solve
from .report.writeup import limits_md
from .runner.account import Accountant
from .runner.evaluate import DISCLAIMER, TaskRun, load_task_package, run_task
from .runner.guards import HoldoutPathError, assert_items_not_holdout, assert_no_holdout
from .runner.manifest import (
    build_manifest,
    item_content_hash,
    item_line_hash,
    trajectory_hash,
    write_run,
)
from .runner.with_judge import apply_judge
from .scale import fmt2
from .smoke import format_report, run_smoke
from .validate.items import load_items_file, validate_items_dir
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
        # P1 收尾：Judge / 混分开关
        e.add_argument("--with-judge", action="store_true", help="启用 Judge 后处理（机检/Judge 分列）")
        e.add_argument("--judge", choices=("mock", "openai"), default="mock", help="Judge 后端")
        e.add_argument("--judge-id", default=None, help="Judge 标识（进 manifest 与 limits）")
        e.add_argument("--k-pass", type=int, default=2, help="主观题 Judge 次数（§8.2 默认 2）")
        e.add_argument("--blend", choices=("parallel", "weighted"), default="parallel",
                       help="默认 parallel 分列不混分；weighted 显式 0.7/0.3 加权")

    d = sub.add_parser("run-dialog", help="τ-Jud 多轮会话（user_seed / model_seed 分列 + pass^k）")
    d.add_argument("--task", required=True)
    d.add_argument("--model", default="mock:dialog", help="mock:dialog / mock:gold / openai:<model>")
    d.add_argument("--items-root", default="data/public")
    d.add_argument("--tasks-root", default="tasks")
    d.add_argument("--lawkb", default=DEFAULT_LAWKB)
    d.add_argument("--out", default=None)
    d.add_argument("--base-url", default=None)
    d.add_argument("--revision", default=None)
    d.add_argument("--temperature", type=float, default=0.0)
    d.add_argument("--seed", type=int, default=None, help="model_seed")
    d.add_argument("--user-seed", type=int, default=42, help="模拟用户种子（与 model seed 分列）")
    d.add_argument("--user-script", default=None, help="缺省取任务包 user_scripts/ 下第一份")
    d.add_argument("--k-pass", type=int, default=3, help="同题复跑次数（pass^k）")

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


# ---------- run / run-all（P0b 机检 + P1 Judge/守卫） ----------


def _make_adapter_factory(args: argparse.Namespace, store: LawkbStore):
    if args.model == "mock:gold":
        return lambda item: mock_gold_adapter(item, store)
    if args.model == "mock:tools":
        return lambda item: mock_tools_adapter(item, store)
    if args.model == "mock:dialog":
        return lambda item: mock_dialog_adapter(item, store)
    if args.model.startswith("openai:"):
        adapter = OpenAICompatAdapter(
            args.model.split(":", 1)[1], base_url=args.base_url, revision=args.revision
        )
        return lambda item: adapter
    raise SystemExit(
        f"未知模型规格: {args.model!r}（支持 mock:gold / mock:tools / mock:dialog / openai:<model>）"
    )


def _make_judge(args: argparse.Namespace):
    """--with-judge 时构造 Judge；mock 模型不得充当 openai Judge。"""
    if not args.with_judge:
        return None
    if args.judge == "mock":
        return MockJudge(judge_id=args.judge_id or "mock-judge", k_pass=args.k_pass)
    if not args.model.startswith("openai:"):
        raise SystemExit("--judge openai 需要 openai:<model> 作为 Judge 模型；mock 跑法请用 --judge mock")
    adapter = OpenAICompatAdapter(
        args.model.split(":", 1)[1], base_url=args.base_url, revision=args.revision
    )
    return OpenAIJudge(adapter, judge_id=args.judge_id or "openai-judge", k_pass=args.k_pass)


def _build_summary(
    args: argparse.Namespace,
    runs: list[TaskRun],
    manifest: dict,
    accountant: Accountant,
    judge_scores: dict[str, dict],
) -> dict:
    """机检/Judge 分列 + 诊断掉分 + Abst + 成本 + 污染（impl-P1-rest §3）。"""
    from .metrics.aggregate import TaskScores, summarize

    per_task: dict[str, dict] = {}
    for run in runs:
        machine = [r.score for r in run.results if r.score is not None]
        judged = [jr.mapped for jr in judge_scores.get(run.task_id, {}).values() if jr is not None]
        ts = TaskScores(task_id=run.task_id, machine=machine, judge=judged)
        row = summarize([ts])["tasks"][0]
        entry = {
            "machine_mean_str": row["machine_mean_str"],
            "judge_mean_str": row["judge_mean_str"],
            "n_machine": row["n_machine"],
            "n_judge": row["n_judge"],
        }
        if args.blend == "weighted":
            combined = combine(ts.mean_machine(), ts.mean_judge(), mode="weighted")
            entry["combined_str"] = fmt2(combined) if combined is not None else "n/a"
        per_task[run.task_id] = entry

    diagnostics: dict[str, dict] = {}
    for run in runs:
        diag = [r.diag_score for r in run.results if r.diag_score is not None]
        if not diag:
            continue
        main = [r.score for r in run.results if r.score is not None and r.diag_score is not None]
        drop, alert = diagnostic_drop(sum(main) / len(main), sum(diag) / len(diag))
        diagnostics[run.task_id] = {
            "diag_drop": fmt2(drop),
            "reward_hacking_alert": alert,
        }

    n_all = sum(len(r.results) for r in runs)
    n_refuse = sum(1 for r in runs for x in r.results if x.abst_over_refuse)
    n_promise = sum(1 for r in runs for x in r.results if x.abst_over_promise)
    scores_flat = [x.score for r in runs for x in r.results if x.score is not None]
    # 无价格表（est_cost_usd=None）时禁编造 $/solve
    est = accountant.est_cost_usd
    dps = dollar_per_solve(est, scores_flat) if est is not None else None
    summary = {
        "run_id": manifest["run_id"],
        "created_at": manifest["created_at"],
        "model_id": args.model,
        "per_task": per_task,
        "tasks": {
            run.task_id: {
                "items": [
                    {
                        "id": x.item_id,
                        "score": x.display,
                        "judge": (judge_scores[run.task_id][x.item_id].mapped_str
                                  if judge_scores.get(run.task_id, {}).get(x.item_id) is not None
                                  else "n/a"),
                        "taxonomy": x.taxonomy,
                        "error": x.error,
                        "predicates": x.predicate_lines,
                    }
                    for x in run.results
                ],
                "mean": fmt2(run.mean) if run.mean is not None else "n/a",
                "n": len(run.results),
            }
            for run in runs
        },
        "diagnostics": diagnostics,
        "abst": {
            "over_refuse_rate": fmt2(100.0 * n_refuse / n_all) if n_all else "n/a",
            "over_promise_rate": fmt2(100.0 * n_promise / n_all) if n_all else "n/a",
        },
        "cost": {
            # 单次 run 无同题复跑，pass^k 不诚实计算 → 留空；复跑稳定性走 flip/成本脚本
            "pass_k": None,
            "dollar_per_solve": fmt2(dps) if dps is not None else None,
            "p95_latency_ms": accountant.p95_latency_ms,
        },
        "contamination": {
            "hits": [asdict(h) for r in runs for x in r.results for h in x.contamination],
        },
        "slice_union_hash": manifest["lawkb"]["slice_union_hash"],
        "disclaimer": DISCLAIMER,
    }
    return summary


def _execute_runs(args: argparse.Namespace, task_ids: list[str]) -> tuple[list[TaskRun], dict]:
    store = _load_store(args.lawkb)
    factory = _make_adapter_factory(args, store)
    accountant = Accountant()
    judge = _make_judge(args)
    runs: list[TaskRun] = []
    prompts: list[str] = []
    raw_lines: list[str] = []
    item_hashes: dict[str, str] = {}
    all_items = []
    task_dirs: dict[str, Path] = {}

    for tid in task_ids:
        task_dir = Path(args.tasks_root) / tid
        items_path = Path(args.items_root) / f"{tid}.jsonl"
        task, _ = load_task_package(task_dir)
        task_dirs[tid] = task_dir
        for line in items_path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                raw_lines.append(line)
        for _lineno, item in load_items_file(items_path):
            all_items.append(item)
            prompts.append(task.prompt_template.replace("{input}", item.input))
        for _lineno, item in load_items_file(items_path):
            raw = next((ln for ln in raw_lines if f'"{item.id}"' in ln or f"'{item.id}'" in ln), item.input)
            item_hashes[item.id] = item_line_hash(item.id, raw)
        runs.append(
            run_task(
                task_dir, items_path, factory, store,
                temperature=args.temperature, seed=args.seed, accountant=accountant,
            )
        )

    # holdout 守卫第二层：题面 split（路径层在 _cmd_run_generic 入口已查）
    assert_items_not_holdout(all_items)

    # P1：Judge 后处理（judge_calls/judge tokens 记账后建 manifest，口径一致）
    judge_scores: dict[str, dict] = {}
    if judge is not None:
        rubrics = {tid: load_rubric(d) for tid, d in task_dirs.items()}
        judge_scores = apply_judge(runs, judge, rubrics, accountant=accountant, k_pass=args.k_pass)

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
        user_seed=getattr(args, "user_seed", None),
        item_hashes=item_hashes,
        trajectory_hashes={
            x.item_id: trajectory_hash(x.trajectory)
            for r in runs for x in r.results if x.trajectory is not None
        } or None,
    )
    summary = _build_summary(args, runs, manifest, accountant, judge_scores)
    return runs, {"manifest": manifest, "summary": summary, "judge": judge,
                  "unknown_in_lawkb": sum(
                      1 for r in runs for x in r.results
                      if any("unknown_in_lawkb" in line for line in x.predicate_lines))}


def _limits_text(args: argparse.Namespace, artifacts: dict) -> str:
    judge = artifacts.get("judge")
    if judge is not None:
        bias = (f"{judge.judge_id}（k_pass={args.k_pass}，prompt_hash={judge.prompt_hash}）；"
                "正式对比前须换真 Judge 并双盲校准")
    else:
        bias = "本次 run 未启用 Judge（--with-judge）"
    return limits_md(
        flip_rate=None,  # 单跑不测翻转；复跑测定走 scripts/flip_rate_check.py
        unknown_in_lawkb=artifacts["unknown_in_lawkb"],
        judge_bias=bias,
        pending_text_review=[],
    )


def _print_runs(runs: list[TaskRun], artifacts: dict) -> None:
    judge_scores = artifacts["summary"].get("per_task", {})
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
    for tid, entry in judge_scores.items():
        print(f"{tid} judge_mean: {entry['judge_mean_str']} (n_judge={entry['n_judge']})")
    print(f"slice_union_hash={artifacts['manifest']['lawkb']['slice_union_hash']}")
    print(f"manifest={artifacts['manifest']['run_id']} harness={artifacts['manifest']['harness_sha']}")
    print(DISCLAIMER)


def _cmd_run_generic(args: argparse.Namespace) -> int:
    task_ids = [args.task] if hasattr(args, "task") else [t.strip() for t in args.tasks.split(",") if t.strip()]
    try:
        assert_no_holdout(args.items_root, args.tasks_root, args.lawkb)
        runs, artifacts = _execute_runs(args, task_ids)
    except HoldoutPathError as e:
        print(f"HOLDOUT GUARD: {e}")
        return 2
    out_dir = Path(args.out) if args.out else Path("reports/runs") / artifacts["manifest"]["run_id"]
    trajectories = {
        x.item_id: x.trajectory for r in runs for x in r.results if x.trajectory is not None
    }
    write_run(out_dir, artifacts["manifest"], artifacts["summary"],
              limits_text=_limits_text(args, artifacts),
              trajectories=trajectories or None)
    _print_runs(runs, artifacts)
    written = f"{out_dir}/manifest.json, {out_dir}/summary.json, {out_dir}/limits.md"
    if trajectories:
        written += f", {out_dir}/items/*.trajectory.json (×{len(trajectories)})"
    print(f"written: {written}")
    na = sum(1 for run in runs for r in run.results if r.score is None)
    # 自动刷新可视化面板（可选；失败不影响评测结果）
    try:
        import subprocess
        import sys as _sys

        subprocess.run(
            [_sys.executable, str(Path(__file__).resolve().parents[2] / "scripts" / "sync_dashboard.py"),
             "--run", str(out_dir)],
            check=False,
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass
    return 1 if na else 0


def _cmd_run_dialog(args: argparse.Namespace) -> int:
    """τ-Jud 多轮：终态 F1 × Proto gate，pass^k 双列 + 方差分解（impl-P3 §2/§6）。"""
    import yaml as _yaml

    from .dialog.session import dump_dialog, run_dialog
    from .metrics.variance import decompose_variance, format_stability, score_time_auc
    from .schemas.user_script import UserScript

    try:
        assert_no_holdout(args.items_root, args.tasks_root, args.lawkb)
    except HoldoutPathError as e:
        print(f"HOLDOUT GUARD: {e}")
        return 2

    store = _load_store(args.lawkb)
    task_dir = Path(args.tasks_root) / args.task
    items_path = Path(args.items_root) / f"{args.task}.jsonl"
    if not items_path.is_file():
        print(f"DIALOG FAIL: 题面不存在 {items_path}")
        return 1

    us_dir = task_dir / "user_scripts"
    if args.user_script:
        us_path = Path(args.user_script)
    else:
        cands = sorted(us_dir.glob("*.yaml")) if us_dir.is_dir() else []
        if not cands:
            print(f"DIALOG FAIL: 未找到 user_scripts（{us_dir}）")
            return 1
        us_path = cands[0]
    script = UserScript.model_validate(_yaml.safe_load(us_path.read_text(encoding="utf-8")))

    factory = _make_adapter_factory(args, store)
    accountant = Accountant()
    items = [it for _ln, it in load_items_file(items_path)]
    assert_items_not_holdout(items)

    from .dialog.session import DialogResult

    # 两套复跑：固定 user_seed（模型稳定度） vs 轮换 user_seed（交互稳定度）
    fixed_runs: dict[str, list[float]] = {it.id: [] for it in items}
    swap_runs: dict[str, list[float]] = {it.id: [] for it in items}
    last: dict[str, DialogResult] = {}
    trajectories: dict[str, dict] = {}
    model_scores: list[float] = []
    user_scores: list[float] = []

    for item in items:
        for k in range(max(1, args.k_pass)):
            r_fix = run_dialog(
                item, script, factory(item),
                user_seed=args.user_seed, model_seed=args.seed,
                temperature=args.temperature, accountant=accountant,
            )
            if r_fix.score is not None:
                fixed_runs[item.id].append(r_fix.score)
                model_scores.append(r_fix.score)
            last[f"{item.id}#f{k}"] = r_fix
            trajectories[f"{item.id}.f{k}"] = dump_dialog(r_fix)

            r_swap = run_dialog(
                item, script, factory(item),
                user_seed=args.user_seed + 1 + k, model_seed=args.seed,
                temperature=args.temperature, accountant=accountant,
            )
            if r_swap.score is not None:
                swap_runs[item.id].append(r_swap.score)
                user_scores.append(r_swap.score)
            last[f"{item.id}#s{k}"] = r_swap
            trajectories[f"{item.id}.s{k}"] = dump_dialog(r_swap)

        # 主展示列 = 固定 user_seed 的第一次
        last[item.id] = last[f"{item.id}#f0"]

    from .metrics.cost import pass_at_k as _pak

    def _bool_runs(scores: list[float], k: int) -> list[list[bool]]:
        return [[s >= 60.0 for s in sc[:k]] for sc in scores.values()]

    k = max(1, args.k_pass)
    pk_model = _pak(_bool_runs(fixed_runs, k), k=k)
    pk_user = _pak(_bool_runs(swap_runs, k), k=k)
    var = decompose_variance(model_scores=model_scores, user_scores=user_scores)

    # score–time：若有进度点则算 AUC，否则 n/a（不编造）
    st_points = [
        (1.0, (r.state_f1 if r.state_f1 is not None else 0.0))
        for r in last.values() if isinstance(r, DialogResult) and not r.item_id.endswith("0")
    ]
    st_auc = score_time_auc([(0.0, 0.0), (1.0, sum(x[1] for x in st_points) / max(1, len(st_points)))] ) if st_points else None

    scores = [last[it.id].score for it in items if last[it.id].score is not None]
    mean = sum(scores) / len(scores) if scores else None
    summary = {
        "task_id": args.task,
        "model_id": args.model,
        "user_seed": args.user_seed,
        "model_seed": args.seed,
        "k_pass": k,
        "n_items": len(items),
        "mean_str": fmt2(mean) if mean is not None else "n/a",
        "items": [
            {
                "id": it.id,
                "score": last[it.id].display,
                "state_f1": fmt2(100.0 * last[it.id].state_f1),
                "proto_redline": last[it.id].proto.redline,
                "taxonomy": last[it.id].taxonomy,
                "n_turns": last[it.id].n_turns,
            }
            for it in items
        ],
        "stability": format_stability(
            pass_k_model=pk_model, pass_k_user=pk_user, variance=var,
            lawyer_baseline="未测",
        ),
        "score_time_auc_str": fmt2(st_auc) if st_auc is not None else "n/a",
        "score_time_auc_note": "approx" if st_auc is not None else None,
        "disclaimer": DISCLAIMER,
    }

    run_id = f"dialog-{args.task}-{args.user_seed}"
    out_dir = Path(args.out) if args.out else Path("reports/runs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # §7.1：复用 build_manifest（harness/prompt/lawkb/slice 与 run 一致），并显式记 seeds
    from .runner.evaluate import TaskRun
    from .runner.manifest import build_manifest, item_line_hash, write_run

    task_prompts = []
    item_hashes = {}
    raw_lines = []
    for _ln, it in load_items_file(items_path):
        task, _ = load_task_package(task_dir)
        task_prompts.append(task.prompt_template.replace("{input}", it.input))
        raw_lines.append(it.model_dump_json())
        item_hashes[it.id] = item_line_hash(it.id, it.model_dump_json())
    fake_run = TaskRun(task_id=args.task, results=[])
    manifest = build_manifest(
        runs=[fake_run],
        store_version=store.store_version,
        model_id=args.model,
        revision=args.revision,
        temperature=args.temperature,
        seed=args.seed,
        prompt_list=task_prompts,
        item_count=len(items),
        content_hash=item_content_hash(raw_lines),
        accountant=accountant,
        user_seed=args.user_seed,
        item_hashes=item_hashes,
        extra={
            "kind": "tau_jud_dialog",
            "model_seed": args.seed,
            "user_script_id": script.script_id,
            "k_pass": k,
        },
    )
    write_run(
        out_dir, manifest, summary,
        limits_text=(
            f"# limits\n\n- user_seed={args.user_seed} / model_seed={args.seed}（分列）\n"
            f"- pass^k 固定用户={fmt2(100 * pk_model)} / 换 persona={fmt2(100 * pk_user)}\n"
            f"- 方差分解: {var}\n- 律师基线：未测\n\n{DISCLAIMER}\n"
        ),
        trajectories={
            f"{key}.dialog": payload for key, payload in trajectories.items()
        } or None,
    )

    for it in items:
        r = last[it.id]
        tax = f"\t{','.join(r.taxonomy)}" if r.taxonomy else ""
        print(f"{args.task}\t{it.id}\t{r.display}\tF1={fmt2(100 * r.state_f1)}{tax}")
    print(f"{args.task} mean: {summary['mean_str']} (n={len(items)})")
    print(f"pass^k fixed_user={summary['stability']['pass_k_fixed_user_str']} "
          f"swapped={summary['stability']['pass_k_swapped_persona_str']}")
    print(f"user_seed={args.user_seed} model_seed={args.seed}")
    print(DISCLAIMER)
    print(f"written: {out_dir}/manifest.json, summary.json, limits.md")
    return 0 if mean is not None else 1


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
        "run-dialog": _cmd_run_dialog,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

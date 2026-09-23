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

from .adapters.file_answers import FileAnswersAdapter, HashedFileAnswersAdapter
from .adapters.mock import mock_dialog_adapter, mock_gold_adapter, mock_tools_adapter
from .adapters.openai_compat import OpenAICompatAdapter
from .judge import MockJudge, load_rubric
from .judge.openai_judge import OpenAIJudge
from .lawkb.resolve import resolve_article
from .lawkb.store import LawkbStore
from .metrics.aggregate import combine, diagnostic_drop
from .metrics.cost import dollar_per_solve
from .providers import apply_profile_to_args, load_env_local, resolve_profile
from .report.writeup import limits_md
from .runner.account import Accountant, price_key_from_model
from .runner.evaluate import DISCLAIMER, TaskRun, load_task_package, run_task, run_tasks, scored_rate_stats
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
        e.add_argument("--model", required=True, help="mock:gold / openai:<model> / file:<答案目录>")
        e.add_argument("--items-root", default="data/public")
        e.add_argument("--tasks-root", default="tasks")
        e.add_argument("--lawkb", default=DEFAULT_LAWKB)
        e.add_argument("--out", default=None, help="默认 reports/runs/<run_id>")
        e.add_argument("--base-url", default=None)
        e.add_argument("--revision", default=None)
        e.add_argument("--temperature", type=float, default=0.0)
        e.add_argument("--seed", type=int, default=None)
        e.add_argument("--concurrency", type=int, default=1,
                       help="评测线程池大小（1=串行；真实 API 可调高，如 50）")
        e.add_argument("--reasoning-effort", default=None,
                       choices=("low", "medium", "high", "max"),
                       help="思考强度（智谱 reasoning_effort；GLM-5.3-Flash 推荐 max）")
        e.add_argument("--timeout", type=float, default=60.0,
                       help="单次 API 超时秒（思考模型建议 ≥180）")
        e.add_argument("--provider", default=None,
                       help="提供商（configs/providers.yaml：deepseek / zhipu …）")
        # L2 污染检测（DESIGN v0.4 §7）：题面 vs 参考语料 n-gram 重叠
        e.add_argument("--ngram-corpus", default=None,
                       help="参考语料文件（空行分篇文本）；不传则 contamination.ngram_overlap=n/a")
        e.add_argument("--ngram-size", type=int, default=8, help="字符 n-gram 长度")
        # P1 收尾：Judge / 混分开关
        e.add_argument("--with-judge", action="store_true", help="启用 Judge 后处理（机检/Judge 分列）")
        e.add_argument("--judge", default="mock",
                       help="Judge 后端：mock / openai / file:<judge答案目录>（按 sha256(judge prompt) 寻址）")
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

    cmp_ = sub.add_parser("compare", help="两 run 同题配对比较（分差 bootstrap CI + McNemar）")
    cmp_.add_argument("--run-a", required=True, help="run A 目录（含 summary.json）")
    cmp_.add_argument("--run-b", required=True, help="run B 目录（含 summary.json）")
    cmp_.add_argument("--threshold", type=float, default=60.0,
                      help="McNemar 通过阈值（缺省 60，同 report.csv solve 口径）")
    cmp_.add_argument("--out", type=Path, default=None, help="compare.json 输出路径")

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
    if args.model.startswith("file:"):
        # 外部作答回灌：答案按 <dir>/<item_id>.txt 寻址（subagent 考生等场景）
        answers_dir = Path(args.model.split(":", 1)[1])
        return lambda item: FileAnswersAdapter(item.id, answers_dir)
    if args.model.startswith("openai:"):
        effort = getattr(args, "reasoning_effort", None)
        thinking = getattr(args, "_cnjb_thinking", None)
        if effort and not thinking:
            thinking = {"type": "enabled", "clear_thinking": False}
        adapter = OpenAICompatAdapter(
            args.model.split(":", 1)[1], base_url=args.base_url, revision=args.revision,
            reasoning_effort=effort, thinking=thinking,
            timeout=getattr(args, "timeout", 60.0),
            api_key=(getattr(args, "_cnjb_profile", {}) or {}).get("api_key"),
        )
        return lambda item: adapter
    raise SystemExit(
        f"未知模型规格: {args.model!r}（支持 mock:gold / mock:tools / mock:dialog / openai:<model> / file:<答案目录>）"
    )


def _make_judge(args: argparse.Namespace):
    """--with-judge 时构造 Judge；mock 模型不得充当 openai Judge。"""
    if not args.with_judge:
        return None
    spec = args.judge
    if spec == "mock":
        return MockJudge(judge_id=args.judge_id or "mock-judge", k_pass=args.k_pass)
    if spec.startswith("file:"):
        # 外部作答回灌 Judge（subagent 裁判）：文件按 sha256(judge prompt) 寻址
        j_adapter = HashedFileAnswersAdapter(Path(spec.split(":", 1)[1]))
        return OpenAIJudge(j_adapter, judge_id=args.judge_id or "subagent-judge", k_pass=args.k_pass)
    if spec == "openai":
        if not args.model.startswith("openai:"):
            raise SystemExit("--judge openai 需要 openai:<model> 作为 Judge 模型；mock 跑法请用 --judge mock")
        effort = getattr(args, "reasoning_effort", None)
        adapter = OpenAICompatAdapter(
            args.model.split(":", 1)[1], base_url=args.base_url, revision=args.revision,
            reasoning_effort=effort,
            thinking={"type": "enabled", "clear_thinking": False} if effort else None,
        )
        return OpenAIJudge(adapter, judge_id=args.judge_id or "openai-judge", k_pass=args.k_pass)
    raise SystemExit(
        f"未知 --judge 规格: {spec!r}（支持 mock / openai / file:<judge答案目录>）"
    )


def _build_summary(
    args: argparse.Namespace,
    runs: list[TaskRun],
    manifest: dict,
    accountant: Accountant,
    judge_scores: dict[str, dict],
    baseline_runs: dict[str, list[TaskRun]] | None = None,
) -> dict:
    """机检/Judge 分列 + safety/hard/CI + baselines + 诊断掉分 + Abst + 成本 + 污染。

    DESIGN v0.4 §4.3：主分 = capability（不含 safety 夹具）；safety 单列；
    hard = difficulty≥3 子集；机检均值恒附 bootstrap 95% CI；
    §6.3：baselines 两列（random/rules，同判分管线口径）。
    """
    from .metrics.aggregate import TaskScores, summarize
    from .metrics.bootstrap import bootstrap_ci_mean

    def _mean(xs: list[float]) -> float | None:
        return sum(xs) / len(xs) if xs else None

    per_task: dict[str, dict] = {}
    cap_all: list[float] = []
    hard_all: list[float] = []
    safety_all: list[float] = []
    for run in runs:
        cap = [r for r in run.results if r.role != "safety" and r.score is not None]
        safety = [r for r in run.results if r.role == "safety" and r.score is not None]
        hard = [r for r in cap if r.difficulty >= 3]
        machine = [r.score for r in cap]
        judged = [jr.mapped for jr in judge_scores.get(run.task_id, {}).values() if jr is not None]
        ts = TaskScores(task_id=run.task_id, machine=machine, judge=judged)
        row = summarize([ts])["tasks"][0]
        entry = {
            "machine_mean": row["machine_mean"],
            "machine_mean_str": row["machine_mean_str"],
            "judge_mean_str": row["judge_mean_str"],
            "n_machine": row["n_machine"],
            "n_judge": row["n_judge"],
            "solve_rate_str": (
                fmt2(100.0 * sum(1 for s in machine if s >= 60.0) / len(machine))
                if machine else "n/a"
            ),
        }
        if machine:
            ci = bootstrap_ci_mean(machine)
            entry["machine_ci95"] = [fmt2(ci["ci95_low"]), fmt2(ci["ci95_high"])]
        else:
            entry["machine_ci95"] = None
        entry["hard_mean_str"] = fmt2(_mean([r.score for r in hard])) if hard else "n/a"
        entry["n_hard"] = len(hard)
        entry["safety_mean_str"] = fmt2(_mean([r.score for r in safety])) if safety else "n/a"
        entry["n_safety"] = len(safety)
        # v0.6 n/a 口径：scored_rate / n-a计0保守均值 / 低scored率告警
        entry.update(scored_rate_stats(run.results))
        if args.blend == "weighted":
            combined = combine(ts.mean_machine(), ts.mean_judge(), mode="weighted")
            entry["combined_str"] = fmt2(combined) if combined is not None else "n/a"
        per_task[run.task_id] = entry
        cap_all += machine
        hard_all += [r.score for r in hard]
        safety_all += [r.score for r in safety]

    # grand（§4.3）：维等权 macro（任务包等权）与题量加权 micro 分列；hard 子集附 CI
    task_means = [per_task[r.task_id]["machine_mean"] for r in runs
                  if isinstance(per_task[r.task_id].get("machine_mean"), float)]
    grand_eq = _mean(task_means)
    grand_w = _mean(cap_all)
    grand_hard = _mean(hard_all)
    hard_ci = bootstrap_ci_mean(hard_all) if len(hard_all) >= 2 else None
    capability = {
        "grand_eq": fmt2(grand_eq) if grand_eq is not None else "n/a",
        "grand_w": fmt2(grand_w) if grand_w is not None else "n/a",
        "hard": fmt2(grand_hard) if grand_hard is not None else "n/a",
        "hard_ci95": [fmt2(hard_ci["ci95_low"]), fmt2(hard_ci["ci95_high"])] if hard_ci else None,
        "n_capability": len(cap_all),
        "n_hard": len(hard_all),
        "n_safety": len(safety_all),
    }

    # baselines 两列（§6.3）：同判分管线口径；未覆盖任务不计入均值
    baselines: dict[str, dict] = {}
    for kind, bruns in sorted((baseline_runs or {}).items()):
        b_means = [r.mean for r in bruns if r.mean is not None]
        b_all = [x.score for r in bruns for x in r.capability_results if x.score is not None]
        b_safety = [x.score for r in bruns for x in r.safety_results if x.score is not None]
        baselines[kind] = {
            "grand_eq": fmt2(_mean(b_means)) if b_means else "n/a",
            "grand_w": fmt2(_mean(b_all)) if b_all else "n/a",
            "safety_score": fmt2(_mean(b_safety)) if b_safety else "n/a",
            "per_task": {r.task_id: (fmt2(r.mean) if r.mean is not None else "n/a") for r in bruns},
        }

    diagnostics: dict[str, dict] = {}
    for run in runs:
        diag = [r.diag_score for r in run.results if r.diag_score is not None]
        if not diag:
            continue
        main = [r.score for r in run.results if r.score is not None and r.diag_score is not None]
        drop, alert = diagnostic_drop(sum(main) / len(main), sum(diag) / len(diag))
        diagnostics[run.task_id] = {
            "diag_drop": fmt2(drop),
            "diag_diff_raw": fmt2(sum(main) / len(main) - sum(diag) / len(diag)),  # 含负值，如实披露
            "reward_hacking_alert": alert,
        }

    n_all = sum(len(r.results) for r in runs)
    n_refuse = sum(1 for r in runs for x in r.results if x.abst_over_refuse)
    n_promise = sum(1 for r in runs for x in r.results if x.abst_over_promise)
    scores_flat = [x.score for r in runs for x in r.capability_results if x.score is not None]
    # 无价目（est_cost_usd=None）时禁编造 $/solve
    ledger = accountant.cost_ledger()
    est = ledger["est_cost_usd"]
    dps = dollar_per_solve(est, scores_flat) if est is not None else None
    summary = {
        "run_id": manifest["run_id"],
        "created_at": manifest["created_at"],
        "model_id": args.model,
        "temperature": args.temperature,
        # DESIGN v0.4 §8：provisional 产物不得进对外对比表
        "provisional": manifest.get("provisional", True),
        "capability": capability,
        "safety_score": fmt2(_mean(safety_all)) if safety_all else "n/a",
        "baselines": baselines,
        "per_task": per_task,
        "tasks": {
            run.task_id: {
                "items": [
                    {
                        "id": x.item_id,
                        "role": x.role,
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
                "safety_mean": fmt2(run.safety_mean) if run.safety_mean is not None else "n/a",
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
            "dollar_per_solve": (f"{dps:.4f}" if dps is not None else None),
            **ledger,
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
    judge = _make_judge(args)
    accountant = Accountant(
        price_key=(
            getattr(args, "_cnjb_price_key", None) or price_key_from_model(args.model)
        ),
        judge_price_key=(
            (getattr(args, "_cnjb_price_key", None) or price_key_from_model(args.model))
            if judge is not None and args.judge == "openai"
            else None
        ),
    )
    accountant.start_timer()
    runs: list[TaskRun] = []
    prompts: list[str] = []
    raw_lines: list[str] = []
    item_hashes: dict[str, str] = {}
    all_items = []
    task_dirs: dict[str, Path] = {}
    jobs: list[tuple[str, Path, Path]] = []

    for tid in task_ids:
        task_dir = Path(args.tasks_root) / tid
        items_path = Path(args.items_root) / f"{tid}.jsonl"
        task, _ = load_task_package(task_dir)
        task_dirs[tid] = task_dir
        jobs.append((tid, task_dir, items_path))
        for line in items_path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                raw_lines.append(line)
        for _lineno, item in load_items_file(items_path):
            all_items.append(item)
            prompts.append(task.prompt_template.replace("{input}", item.input))
        for _lineno, item in load_items_file(items_path):
            raw = next((ln for ln in raw_lines if f'"{item.id}"' in ln or f"'{item.id}'" in ln), item.input)
            item_hashes[item.id] = item_line_hash(item.id, raw)

    workers = max(1, int(getattr(args, "concurrency", 1) or 1))
    runs = run_tasks(
        jobs, factory, store,
        temperature=args.temperature, seed=args.seed,
        accountant=accountant, max_workers=workers,
    )

    # baselines 两列（DESIGN v0.4 §6.3）：random/rules 走同一判分管线；
    # 适配器本地出答案，零 API 成本。工具轨/多轮轨不适用，跳过。
    from .baselines import SUPPORTED_TASKS, baseline_adapter_factory

    baseline_runs: dict[str, list[TaskRun]] = {}
    supported_jobs = [j for j in jobs if j[0] in SUPPORTED_TASKS]
    if supported_jobs:
        for kind in ("random", "rules"):
            baseline_runs[kind] = run_tasks(
                supported_jobs, baseline_adapter_factory(kind), store,
                temperature=0.0, accountant=None, max_workers=1,
            )

    # holdout 守卫第二层：题面 split（路径层在 _cmd_run_generic 入口已查）
    assert_items_not_holdout(all_items)

    # P1：Judge 后处理（judge_calls/judge tokens 记账后建 manifest，口径一致）
    judge_scores: dict[str, dict] = {}
    if judge is not None:
        rubrics = {tid: load_rubric(d) for tid, d in task_dirs.items()}
        items_by_id = {item.id: item for item in all_items}  # v2 prompt：Judge 吃题面+参考答案
        judge_scores = apply_judge(runs, judge, rubrics, accountant=accountant,
                                   k_pass=args.k_pass, items_by_id=items_by_id)

    accountant.stop_timer()
    # DESIGN v0.4 §8：stats/judge 块进 manifest；provisional 由缺件情况自动判定
    from .metrics.bootstrap import bootstrap_ci_mean

    cap_scores = [x.score for r in runs for x in r.results
                  if x.role == "capability" and x.score is not None]
    cap_ci = bootstrap_ci_mean(cap_scores) if len(cap_scores) >= 2 else None

    def _runs_grand(rs: list[TaskRun]) -> float | None:
        means = [r.mean for r in rs if r.mean is not None]
        return sum(means) / len(means) if means else None

    judge_block = None
    if judge is not None:
        judge_block = {"enabled": True, "model_id": judge.judge_id, "mode": "k_pass",
                       "k_pass": args.k_pass, "prompt_hash": judge.prompt_hash}
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
        judge_block=judge_block,
        stats_block={"ci95": cap_ci, "flip_rate": None, "n_replicates": 1},
        baselines_block={kind: fmt2(_runs_grand(baseline_runs[kind]))
                         for kind in ("random", "rules")} if baseline_runs else None,
        trajectory_hashes={
            x.item_id: trajectory_hash(x.trajectory)
            for r in runs for x in r.results if x.trajectory is not None
        } or None,
    )
    summary = _build_summary(args, runs, manifest, accountant, judge_scores,
                             baseline_runs=baseline_runs)
    # L2 n-gram 污染双检（DESIGN v0.4 §7）：给了语料才实测，否则诚实 n/a
    corpus_ref = getattr(args, "ngram_corpus", None)
    if corpus_ref:
        from .contamination.ngram import load_corpus_ngrams, scan_items_overlap

        rep = scan_items_overlap(
            [(it.id, it.input) for it in all_items],
            load_corpus_ngrams(corpus_ref, n=args.ngram_size), n=args.ngram_size)
        summary.setdefault("contamination", {})["ngram_overlap"] = {
            **rep.as_dict(),
            "max_overlap_str": f"{rep.max_overlap:.4f}",
            "mean_overlap_str": f"{rep.mean_overlap:.4f}",
        }
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
        n_cap = len([r for r in run.capability_results if r.score is not None])
        print(f"{run.task_id} mean: {mean} (n={n_cap}, capability)"
              + (f" [safety {fmt2(run.safety_mean)} n={len(run.safety_results)}]"
                 if run.safety_results else ""))
    for tid, entry in judge_scores.items():
        print(f"{tid} judge_mean: {entry['judge_mean_str']} (n_judge={entry['n_judge']})")
    print(f"slice_union_hash={artifacts['manifest']['lawkb']['slice_union_hash']}")
    print(f"manifest={artifacts['manifest']['run_id']} harness={artifacts['manifest']['harness_sha']}")
    print(DISCLAIMER)


def _write_report_csv(out_dir: Path, summary: dict, manifest: dict) -> None:
    """DESIGN v0.4 §9：导出 report.csv（论文表直贴，列 = §6.1 主表模板 + provisional）。"""
    import csv

    ci = manifest.get("stats", {}).get("ci95") or {}
    cap = summary.get("capability", {})
    solve = solved = 0
    for task in summary.get("tasks", {}).values():
        for it in task.get("items", []):
            if it.get("role") == "safety" or it.get("score") in (None, "n/a"):
                continue
            solve += 1
            solved += 1 if float(it["score"]) >= 60.0 else 0
    cap_str = cap.get("grand_eq", "n/a")
    if ci.get("ci95_low") is not None:
        cap_str = f"{ci['point']:.2f} [{ci['ci95_low']:.2f},{ci['ci95_high']:.2f}]"
    hard_str = cap.get("hard", "n/a")
    if cap.get("hard_ci95"):
        lo, hi = cap["hard_ci95"]
        hard_str = f"{cap['hard']} [{lo},{hi}]"
    ledger = summary.get("cost", {})
    # §6.1 必报列：fail2pass（calc 隐藏单测）/ recovery（tool_fault_recovery）
    # 取该任务在本次 run 中的能力得分；工具轨未跑保持 n/a，不编造。
    def _task_cap(task_id: str) -> str:
        t = summary.get("tasks", {}).get(task_id) or {}
        scores = [float(i["score"]) for i in t.get("items", [])
                  if i.get("score") not in (None, "n/a")]
        return f"{sum(scores) / len(scores):.2f}" if scores else "n/a"

    # v0.6：全任务最差 scored_rate 进主表（n/a 率披露，防「跑完即胜」误读）
    rates = [task.get("scored_rate") for task in summary.get("per_task", {}).values()
             if isinstance(task.get("scored_rate"), float)]
    worst_rate = min(rates) if rates else None
    row = {
        "模型": summary.get("model_id", "n/a"),
        "rev": f"{manifest.get('harness_sha', 'unknown')}"
               f"/{manifest.get('model', {}).get('revision') or '-'}",
        "cap±CI": cap_str,
        "hard±CI": hard_str,
        "safety": summary.get("safety_score", "n/a"),
        "solve%": (f"{100.0 * solved / solve:.2f}" if solve else "n/a"),
        "scored%": (f"{100.0 * worst_rate:.2f}" if worst_rate is not None else "n/a"),
        "e2e%": "n/a",
        "fail2pass%": _task_cap("calc_fail_to_pass"),
        "recovery%": _task_cap("tool_fault_recovery"),
        "$/solve": (ledger.get("dollar_per_solve") or "n/a"),
        "p95": (f"{manifest.get('accounting', {}).get('p95_latency_ms')}" if
                manifest.get("accounting", {}).get("p95_latency_ms") is not None else "n/a"),
        "flip%": "n/a",  # 单跑不测翻转；复跑走 scripts/flip_rate_check.py
        "provisional": manifest.get("provisional", True),
    }
    path = out_dir / "report.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerow(row)


def _cmd_run_generic(args: argparse.Namespace) -> int:
    # 提供商配置：base_url / 默认思考与超时 / 价目键（用户显式参数优先）
    if getattr(args, "model", "") and not str(args.model).startswith(("mock:", "file:")):
        try:
            prof = resolve_profile(args.model, provider_name=getattr(args, "provider", None))
        except SystemExit as e:
            print(e)
            return 2
        apply_profile_to_args(args, prof)
        # 显式 --temperature / --reasoning-effort 保持 CLI 优先
        env_local = load_env_local()
        if not prof.get("api_key"):
            print("缺少 API Key：请设环境变量或写入 .env.local（见 configs/providers.yaml api_key_env）")
            return 2
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
    _write_report_csv(out_dir, artifacts["summary"], artifacts["manifest"])
    _print_runs(runs, artifacts)
    written = f"{out_dir}/manifest.json, {out_dir}/summary.json, {out_dir}/limits.md"
    if trajectories:
        written += f", {out_dir}/items/*.trajectory.json (×{len(trajectories)})"
    print(f"written: {written}")
    na = sum(1 for run in runs for r in run.results if r.score is None)
    # 自动刷新可视化面板（可选；失败不掩盖评测结果，但须留痕可诊断）
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
    except Exception as e:  # noqa: BLE001 —— 面板属附加产物，失败降级为警告
        print(f"dashboard sync 跳过（非致命）: {type(e).__name__}: {e}")
    return 1 if na else 0


def _cmd_run_dialog(args: argparse.Namespace) -> int:
    """τ-Jud 多轮：终态 F1 × Proto gate，pass^k 双列 + 方差分解（impl-P3 §2/§6）。"""
    import yaml as _yaml

    from .dialog.session import dump_dialog, run_dialog
    from .metrics.variance import decompose_variance, format_stability
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
    accountant = Accountant(price_key=price_key_from_model(args.model))
    accountant.start_timer()
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

    accountant.stop_timer()
    from .metrics.cost import pass_power_k as _ppk

    def _bool_runs(scores: list[float], k: int) -> list[list[bool]]:
        return [[s >= 60.0 for s in sc[:k]] for sc in scores.values()]

    k = max(1, args.k_pass)
    pk_model = _ppk(_bool_runs(fixed_runs, k), k=k)
    pk_user = _ppk(_bool_runs(swap_runs, k), k=k)
    var = decompose_variance(model_scores=model_scores, user_scores=user_scores)

    # v0.6 语义修复：原「两点 AUC」数学上恒等于 50×mean(state_f1)，且键过滤
    # 误伤以 0 结尾的真实题——挂 AUC 名会误导读者。改为如实输出终态 state_f1
    # 均值；真实进度点 AUC 待 turn 级 progress 数据（FRAMEWORK §5 原义）。
    final_state_f1_vals = [
        (r.state_f1 if r.state_f1 is not None else 0.0)
        for r in last.values() if isinstance(r, DialogResult) and "#" not in r.item_id
    ]
    final_state_f1_mean = (
        sum(final_state_f1_vals) / len(final_state_f1_vals)
        if final_state_f1_vals else None
    )

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
        "final_state_f1_str": fmt2(100.0 * final_state_f1_mean) if final_state_f1_mean is not None else "n/a",
        "score_time_auc_str": "n/a",
        "score_time_auc_note": "n/a：缺 turn 级进度点，两点近似已于 v0.6 移除（见 final_state_f1）",
        "cost": accountant.cost_ledger(),
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


def _cmd_compare(args: argparse.Namespace) -> int:
    """两 run 同题配对比较（FRAMEWORK §8：分差 CI + McNemar；论文"A 比 B"依据）。"""
    from .metrics.compare import compare_runs

    rep = compare_runs(Path(args.run_a), Path(args.run_b), threshold=args.threshold)
    if "error" in rep:
        print(f"compare: {rep['error']}")
        return 1
    ci = rep["paired_ci"]
    m = rep["mcnemar"]
    print(f"n_aligned={rep['n_aligned']} (only_a={rep['n_only_a']}, only_b={rep['n_only_b']})")
    print(f"mean_a={rep['mean_a']:.2f} mean_b={rep['mean_b']:.2f} "
          f"diff={ci['point']:.2f} [{ci['ci95_low']:.2f}, {ci['ci95_high']:.2f}] "
          f"(n_boot={ci['n_boot']}, seed={ci['seed']})")
    print(f"mcnemar: 01(a错b对)={m['n_01']} 10(a对b错)={m['n_10']} "
          f"p_exact={m['p_exact']:.4f}")
    if args.out:
        args.out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"written: {args.out}")
    sig = "显著（CI 不含 0）" if (ci["ci95_low"] > 0 or ci["ci95_high"] < 0) else "不显著（CI 含 0）"
    print(f"结论：A-B 分差 {sig}")
    return 0


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
        "compare": _cmd_compare,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

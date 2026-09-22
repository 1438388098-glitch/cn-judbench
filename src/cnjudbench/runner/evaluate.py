"""单题判分：prompt → completion → claim 抽取 → CiteGuard → 谓词 → 题分。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from ..adapters.base import CompletionResult, ModelAdapter
from ..citeguard.check import CiteCheck, check_claim
from ..citeguard.extract import extract_claims, parse_answer_json
from ..contamination.canary import ContaminationHit, scan_output
from ..gates.redline import apply_gates, detect_redlines
from ..judge.abst import label_abst
from ..predicates.base import EvalContext, PredicateError
from ..predicates.registry import compose_score, evaluate_predicates
from ..scale import fmt2
from ..schemas.item import Item
from ..schemas.task import PredicatesFile, TaskManifest
from ..tools.sandbox import ToolSandbox
from ..validate.items import load_items_file
from .account import Accountant

DISCLAIMER = "本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。"

JsonTask = tuple[TaskManifest, PredicatesFile]


@dataclass
class ItemResult:
    item_id: str
    score: float | None  # None = 拒判/系统错误（报告 n/a，禁填 0 充数）
    display: str
    taxonomy: list[str] = field(default_factory=list)
    predicate_lines: list[str] = field(default_factory=list)
    as_of_used: list[str] = field(default_factory=list)
    text_hashes: list[str] = field(default_factory=list)  # ok 解析触达的切片
    error: str | None = None
    role: str = "capability"  # capability 进主分；safety 夹具单列 safety_score（DESIGN v0.4 §4.1）
    difficulty: int = 0  # hard 分层（difficulty≥3 进 hard_mean，DESIGN v0.4 §4.3）
    # P1 接线：Judge / Abst / 污染 / 诊断所需的题级现场
    answer_text: str = ""  # with_judge 后处理与 abst/canary 扫描输入
    abst_over_refuse: bool = False
    abst_over_promise: bool = False
    contamination: list[ContaminationHit] = field(default_factory=list)
    diag_score: float | None = None  # diagnostic_ftp 单独合成；无诊断谓词为 None
    trajectory: dict | None = None  # P2：tool_call 题的沙箱调用轨迹（落盘 + hash 进 manifest）


@dataclass
class TaskRun:
    task_id: str
    results: list[ItemResult]

    @property
    def capability_results(self) -> list[ItemResult]:
        """主分题（role=capability）；safety 夹具不进能力分（DESIGN v0.4 §4.1）。"""
        return [r for r in self.results if r.role != "safety"]

    @property
    def safety_results(self) -> list[ItemResult]:
        return [r for r in self.results if r.role == "safety"]

    @property
    def mean(self) -> float | None:
        """能力分均值（不含 safety 夹具、不含拒判 n/a）。"""
        scored = [r.score for r in self.capability_results if r.score is not None]
        return sum(scored) / len(scored) if scored else None

    @property
    def safety_mean(self) -> float | None:
        scored = [r.score for r in self.safety_results if r.score is not None]
        return sum(scored) / len(scored) if scored else None

    @property
    def as_of_used(self) -> list[str]:
        return sorted({x for r in self.results for x in r.as_of_used})

    @property
    def text_hashes(self) -> list[str]:
        return [h for r in self.results for h in r.text_hashes]


def load_task_package(task_dir: Path) -> JsonTask:
    """加载 task.yaml + predicates.yaml（pydantic 校验，失败即抛）。"""
    task = TaskManifest.model_validate(
        yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8-sig"))
    )
    preds = PredicatesFile.model_validate(
        yaml.safe_load((task_dir / "predicates.yaml").read_text(encoding="utf-8-sig"))
    )
    return task, preds


def _build_prompt(task: TaskManifest, item: Item) -> str:
    # prompt_template 含 JSON 花括号示例，禁用 str.format；只替换 {input} 占位符
    if "{input}" not in task.prompt_template:
        raise ValueError(f"任务 {task.task_id} 的 prompt_template 缺少 {{input}} 占位符")
    return task.prompt_template.replace("{input}", item.input)


def evaluate_item(
    task: TaskManifest,
    preds: PredicatesFile,
    item: Item,
    adapter: ModelAdapter,
    store,
    *,
    temperature: float = 0.0,
    seed: int | None = None,
    accountant: Accountant | None = None,
) -> ItemResult:
    def result(
        score: float | None,
        taxonomy: list[str],
        *,
        error: str | None = None,
        predicate_lines: list[str] | None = None,
        as_of_used: list[str] | None = None,
        text_hashes: list[str] | None = None,
        answer_text: str = "",
        diag_score: float | None = None,
        contamination: list[ContaminationHit] | None = None,
        abst_over_refuse: bool = False,
        abst_over_promise: bool = False,
        trajectory: dict | None = None,
    ) -> ItemResult:
        return ItemResult(
            item_id=item.id,
            score=score,
            display=fmt2(score) if score is not None else "n/a",
            taxonomy=taxonomy,
            predicate_lines=predicate_lines or [],
            as_of_used=as_of_used or [],
            text_hashes=text_hashes or [],
            error=error,
            role=item.role,
            difficulty=item.difficulty,
            answer_text=answer_text,
            diag_score=diag_score,
            contamination=contamination or [],
            abst_over_refuse=abst_over_refuse,
            abst_over_promise=abst_over_promise,
            trajectory=trajectory,
        )

    prompt = _build_prompt(task, item)
    completion = adapter.complete(prompt, temperature=temperature, seed=seed)
    if accountant is not None:
        accountant.add(
            completion.prompt_tokens,
            completion.completion_tokens,
            completion.latency_ms,
            cache_hit_tokens=completion.cache_hit_tokens,
            cache_miss_tokens=completion.cache_miss_tokens,
        )

    # P1 接线：Abst 双标签 + canary 一级扫描（对原始输出，含解析失败路径）
    abst = label_abst(completion.text, expect="answer")
    contam = scan_output(item.id, completion.text, canary=item.canary)
    # P2：tool_call 任务——沙箱随题建，调用日志即轨迹；
    #     gold.initial_state 为案管预置环境（§5.3 在办案件），随题注入；
    #     gold.fault 为故障注入规格（§5.4 tool_fault_recovery）
    _gold = item.gold if isinstance(item.gold, dict) else {}
    sandbox = (ToolSandbox(store, dms_state0=_gold.get("initial_state"),
                           fault=_gold.get("fault"))
               if task.output_type == "tool_call" else None)

    # 1) 答案解析（structured/extract 须为 JSON；容忍 ```json 围栏）。
    #    tool_call 任务解析失败不提前返回：让 fake_tool/终答谓词照常判
    #    （叙述式假调用归 fake_tool 而非 format_fail，负例夹具才可归因）。
    try:
        answer = parse_answer_json(completion.text)
    except ValueError:
        if sandbox is None:
            return result(0.00, ["format_fail"], error="答案不可解析为 JSON",
                          answer_text=completion.text, contamination=contam,
                          abst_over_refuse=abst.over_refuse, abst_over_promise=abst.over_promise)
        answer = None

    # 1.5) P2：tool_call——先执行声称的调用，日志即轨迹与判分事实
    if sandbox is not None:
        calls = answer.get("calls") if isinstance(answer, dict) else None
        for c in calls or []:
            if isinstance(c, dict):
                sandbox.execute(str(c.get("name") or ""), c.get("args"))
        trajectory = {"calls": sandbox.dump(), "answer": answer}
    else:
        trajectory = None

    # 2) claim 抽取 + CiteGuard 三检（claim.as_of 仅在可解析为 ISO 时优先，否则用题面）
    extraction = extract_claims(answer, task.output_type, completion.text)

    def _as_of_for(claim_as_of: str | None) -> str:
        if claim_as_of:
            try:
                from datetime import date as _date
                _date.fromisoformat(str(claim_as_of).strip())
                return str(claim_as_of).strip()
            except ValueError:
                pass  # 「2014年案发时…」等叙述 → 落回题面 as_of
        return item.as_of.isoformat()

    checks: list[CiteCheck] = [
        check_claim(c, store, as_of=_as_of_for(c.as_of)) for c in extraction.claims
    ]
    # as_of_used 记实际生效日（ISO），避免叙述性 claim.as_of 污染 manifest（P2-8）
    as_of_used = [item.as_of.isoformat()] + sorted(
        {
            _as_of_for(c.as_of)
            for c in extraction.claims
            if c.as_of and _as_of_for(c.as_of) != item.as_of.isoformat()
        }
    )
    text_hashes = [chk.text_hash for chk in checks if chk.ok and chk.text_hash]

    if any(chk.ambiguous for chk in checks):
        return result(
            None, [], error="ambiguous_versions：lawkb 多版本同窗（数据错误），拒判报警",
            as_of_used=as_of_used, answer_text=completion.text, contamination=contam,
            abst_over_refuse=abst.over_refuse, abst_over_promise=abst.over_promise,
        )

    # 3) 谓词执行（适用面不符 / 未实现 → 拒判，score = n/a）
    ctx = EvalContext(
        task=task,
        item=item,
        answer=answer,
        answer_text=completion.text,
        claims=extraction.claims,
        claim_status=extraction.status,
        store=store,
        checks=checks,
        tool_log=sandbox.log if sandbox else [],
    )
    try:
        ftp_results, ptp_results, diag_results = evaluate_predicates(ctx, preds)
    except PredicateError as e:
        return result(None, [], error=f"拒判: {e}", as_of_used=as_of_used, text_hashes=text_hashes,
                      answer_text=completion.text, contamination=contam, trajectory=trajectory,
                      abst_over_refuse=abst.over_refuse, abst_over_promise=abst.over_promise)
    except Exception as e:  # noqa: BLE001 —— 单题兜底，禁止崩整卷
        return result(None, [], error=f"谓词异常拒判: {e!r}", as_of_used=as_of_used, text_hashes=text_hashes,
                      answer_text=completion.text, contamination=contam, trajectory=trajectory,
                      abst_over_refuse=abst.over_refuse, abst_over_promise=abst.over_promise)

    score, taxonomy = compose_score(ftp_results, ptp_results)
    # P1 接线：红线 gate（over_promise → 一票否决；顺序：zero 优先于一切 cap）
    if abst.over_promise:
        score, gate_tags = apply_gates(score, detect_redlines(over_promise=True))
        taxonomy = taxonomy + [t for t in gate_tags if t not in taxonomy]
    # DESIGN v0.4 §4.1 ②：应答题空拒（over_refuse）→ 能力分 ×0.50（夹具/safety 题不适用）
    if abst.over_refuse and item.role == "capability" and score is not None:
        score = round(score * 0.50, 4)
        if "over_refuse" not in taxonomy:
            taxonomy = taxonomy + ["over_refuse"]
    # 诊断掉分：diagnostic_ftp 按 pass_ratio 均值合成（多为 flag 级，不走零/封顶语义）
    diag_score = (
        100.0 * sum(r.pass_ratio for r in diag_results) / len(diag_results)
        if diag_results else None
    )
    lines = [
        f"{r.set_name}[{r.index}] {r.type}: {'PASS' if r.passed else 'FAIL'} {r.detail}"
        for r in ftp_results + ptp_results + diag_results
    ]
    return result(score, taxonomy, predicate_lines=lines, as_of_used=as_of_used,
                  text_hashes=text_hashes, answer_text=completion.text,
                  diag_score=diag_score, contamination=contam, trajectory=trajectory,
                  abst_over_refuse=abst.over_refuse, abst_over_promise=abst.over_promise)


def _resolve_predicates(item: Item, task_dir: Path, default: PredicatesFile) -> PredicatesFile:
    """按题分派谓词集：``item.predicates_ref``（L2/L3a 混合任务按题判分）。

    仅允许任务包目录内的相对文件名；禁止绝对路径与 ``..``（P0-5/T-P0-5）。
    解析顺序：任务包目录相对 → 任务包目录同名 basename；
    均不存在 → 拒判级错误（不静默回落默认集，防止判分口径错位）。
    """
    ref = item.predicates_ref
    if not ref:
        return default
    ref_path = Path(ref)
    if ref_path.is_absolute() or ".." in ref_path.parts:
        raise PredicateError(f"predicates_ref 禁止绝对路径或 ..: {ref}（题 {item.id}）")
    task_root = task_dir.resolve()
    candidates = (task_dir / ref, task_dir / Path(ref).name)
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if not resolved.is_relative_to(task_root):
            continue
        if resolved.is_file():
            return PredicatesFile.model_validate(
                yaml.safe_load(resolved.read_text(encoding="utf-8-sig"))
            )
    raise PredicateError(f"predicates_ref 不可解析: {ref}（题 {item.id}）")


def run_task(
    task_dir: Path,
    items_path: Path,
    adapter_factory: Callable[[Item], ModelAdapter],
    store,
    *,
    temperature: float = 0.0,
    seed: int | None = None,
    accountant: Accountant | None = None,
    max_workers: int = 1,
) -> TaskRun:
    task, preds = load_task_package(task_dir)
    entries = list(load_items_file(items_path))

    def _one(entry) -> ItemResult:
        _lineno, item = entry
        return evaluate_item(
            task, _resolve_predicates(item, task_dir, preds), item,
            adapter_factory(item), store,
            temperature=temperature, seed=seed, accountant=accountant,
        )

    if max_workers <= 1:
        results = [_one(e) for e in entries]
    else:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(_one, entries))
    return TaskRun(task_id=task.task_id, results=results)


def run_tasks(
    jobs: list[tuple[str, Path, Path]],
    adapter_factory: Callable[[Item], ModelAdapter],
    store,
    *,
    temperature: float = 0.0,
    seed: int | None = None,
    accountant: Accountant | None = None,
    max_workers: int = 1,
) -> list[TaskRun]:
    """多任务包共享一个线程池（跨包并发，适合 --concurrency 50）。

    ``jobs``：``(task_id, task_dir, items_path)``；返回顺序与 jobs 一致，
    包内题序 = jsonl 原序。
    """
    loaded = []
    for task_id, task_dir, items_path in jobs:
        task, preds = load_task_package(task_dir)
        entries = list(load_items_file(items_path))
        loaded.append((task_id, task, task_dir, preds, entries))

    def _one(task, task_dir, preds, entry) -> ItemResult:
        _lineno, item = entry
        try:
            return evaluate_item(
                task, _resolve_predicates(item, task_dir, preds), item,
                adapter_factory(item), store,
                temperature=temperature, seed=seed, accountant=accountant,
            )
        except Exception as e:  # noqa: BLE001 —— 单题失败不拖垮整批（限流/超时）
            return ItemResult(
                item_id=item.id, score=None, display="n/a",
                predicate_lines=[f"ERROR: {type(e).__name__}: {e}"],
                error=f"{type(e).__name__}: {e}",
            )

    flat = []
    for task_id, task, task_dir, preds, entries in loaded:
        for i, entry in enumerate(entries):
            flat.append((task_id, i, task, task_dir, preds, entry))
    n_per: dict[str, int] = {tid: len(entries) for tid, _t, _d, _p, entries in loaded}

    if max_workers <= 1:
        outs = [_one(t, d, p, e) for _tid, _i, t, d, p, e in flat]
    else:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            outs = list(ex.map(lambda a: _one(a[2], a[3], a[4], a[5]), flat))

    buckets: dict[str, list[ItemResult | None]] = {
        tid: [None] * n for tid, n in n_per.items()
    }
    for (tid, i, *_rest), out in zip(flat, outs):
        buckets[tid][i] = out
    order = [tid for tid, *_ in loaded]
    return [TaskRun(task_id=tid, results=list(buckets[tid])) for tid in order]

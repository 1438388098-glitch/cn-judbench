"""单题判分：prompt → completion → claim 抽取 → CiteGuard → 谓词 → 题分。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from ..adapters.base import CompletionResult, ModelAdapter
from ..citeguard.check import CiteCheck, check_claim
from ..citeguard.extract import extract_claims, parse_answer_json
from ..predicates.base import EvalContext, PredicateError
from ..predicates.registry import compose_score, evaluate_predicates
from ..scale import fmt2
from ..schemas.item import Item
from ..schemas.task import PredicatesFile, TaskManifest
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


@dataclass
class TaskRun:
    task_id: str
    results: list[ItemResult]

    @property
    def mean(self) -> float | None:
        scored = [r.score for r in self.results if r.score is not None]
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
        yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    )
    preds = PredicatesFile.model_validate(
        yaml.safe_load((task_dir / "predicates.yaml").read_text(encoding="utf-8"))
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
        )

    prompt = _build_prompt(task, item)
    completion = adapter.complete(prompt, temperature=temperature, seed=seed)
    if accountant is not None:
        accountant.add(completion.prompt_tokens, completion.completion_tokens, completion.latency_ms)

    # 1) 答案解析（structured/extract 须为 JSON；容忍 ```json 围栏）
    try:
        answer = parse_answer_json(completion.text)
    except ValueError:
        return result(0.00, ["format_fail"], error="答案不可解析为 JSON")

    # 2) claim 抽取 + CiteGuard 三检（claim 无 as_of 时回落题面 as_of）
    extraction = extract_claims(answer, task.output_type, completion.text)
    checks: list[CiteCheck] = [
        check_claim(c, store, as_of=c.as_of or item.as_of.isoformat()) for c in extraction.claims
    ]
    as_of_used = [item.as_of.isoformat()] + [c.as_of for c in extraction.claims if c.as_of]
    text_hashes = [chk.text_hash for chk in checks if chk.ok and chk.text_hash]

    if any(chk.ambiguous for chk in checks):
        return result(
            None, [], error="ambiguous_versions：lawkb 多版本同窗（数据错误），拒判报警",
            as_of_used=as_of_used,
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
    )
    try:
        ftp_results, ptp_results, diag_results = evaluate_predicates(ctx, preds)
    except PredicateError as e:
        return result(None, [], error=f"拒判: {e}", as_of_used=as_of_used, text_hashes=text_hashes)

    score, taxonomy = compose_score(ftp_results, ptp_results)
    lines = [
        f"{r.set_name}[{r.index}] {r.type}: {'PASS' if r.passed else 'FAIL'} {r.detail}"
        for r in ftp_results + ptp_results + diag_results
    ]
    return result(score, taxonomy, predicate_lines=lines, as_of_used=as_of_used, text_hashes=text_hashes)


def run_task(
    task_dir: Path,
    items_path: Path,
    adapter_factory: Callable[[Item], ModelAdapter],
    store,
    *,
    temperature: float = 0.0,
    seed: int | None = None,
    accountant: Accountant | None = None,
) -> TaskRun:
    task, preds = load_task_package(task_dir)
    run = TaskRun(task_id=task.task_id, results=[])
    for _lineno, item in load_items_file(items_path):
        item_result = evaluate_item(
            task, preds, item, adapter_factory(item), store,
            temperature=temperature, seed=seed, accountant=accountant,
        )
        run.results.append(item_result)
    return run

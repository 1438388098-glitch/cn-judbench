"""--with-judge 后处理：对已完成的 run 逐题打 Judge 分（impl-P1-rest §1/§3）。

- 机检分不动；Judge 分单独成列，缺 rubric 的任务 → n/a（禁填 0.00）；
- judge_calls 与 Judge tokens 记入 Accountant（Mock 也计次）；
- 返回 {task_id: {item_id: JudgeResult | None}} 供 summary 组装。
- c395：题级并发（全量 323 题 × k_pass 次串行 API 往返是时长长尾）；
  Accountant 进程内锁与 FileCache 线程安全均支持多线程，MockJudge 无状态。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ..judge import Judge, JudgeResult, Rubric, load_rubric
from .account import Accountant
from .evaluate import TaskRun


def apply_judge(
    runs: list[TaskRun],
    judge: Judge,
    rubrics: dict[str, Rubric | None],
    *,
    accountant: Accountant | None = None,
    k_pass: int = 2,
    items_by_id: dict[str, Any] | None = None,
    concurrency: int = 8,
) -> dict[str, dict[str, JudgeResult | None]]:
    """Judge 后处理。

    items_by_id 提供 item_id → 题对象（含 input/gold）时，Judge prompt v2 会带上
    案情题面与参考答案（去盲判）；查不到的题回退 None（prompt 退化为 rubric+答案）。
    """
    lookup = items_by_id or {}
    out: dict[str, dict[str, JudgeResult | None]] = {run.task_id: {} for run in runs}

    def _score_one(task_id: str, rubric: Rubric | None, r) -> None:
        if rubric is None:
            out[task_id][r.item_id] = None  # 缺 rubric → n/a，禁止 0.00 充数
            return
        item = lookup.get(r.item_id)
        jr = judge.score(
            r.answer_text,
            rubric,
            k_pass=k_pass,
            gold=getattr(item, "gold", None),
            item_input=getattr(item, "input", None),
        )
        if accountant is not None:
            accountant.add_judge(jr.n_calls, jr.prompt_tokens, jr.completion_tokens)
        out[task_id][r.item_id] = jr

    workers = max(1, int(concurrency))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [
            ex.submit(_score_one, run.task_id, rubrics.get(run.task_id), r)
            for run in runs
            for r in run.results
        ]
        for f in futures:
            f.result()
    return out

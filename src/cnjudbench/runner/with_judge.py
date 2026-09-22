"""--with-judge 后处理：对已完成的 run 逐题打 Judge 分（impl-P1-rest §1/§3）。

- 机检分不动；Judge 分单独成列，缺 rubric 的任务 → n/a（禁填 0.00）；
- judge_calls 与 Judge tokens 记入 Accountant（Mock 也计次）；
- 返回 {task_id: {item_id: JudgeResult | None}} 供 summary 组装。
"""

from __future__ import annotations

from pathlib import Path

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
) -> dict[str, dict[str, JudgeResult | None]]:
    out: dict[str, dict[str, JudgeResult | None]] = {}
    for run in runs:
        rubric = rubrics.get(run.task_id)
        per_item: dict[str, JudgeResult | None] = {}
        for r in run.results:
            if rubric is None:
                per_item[r.item_id] = None  # 缺 rubric → n/a，禁止 0.00 充数
                continue
            jr = judge.score(r.answer_text, rubric, k_pass=k_pass)
            if accountant is not None:
                accountant.add_judge(jr.n_calls, jr.prompt_tokens, jr.completion_tokens)
            per_item[r.item_id] = jr
        out[run.task_id] = per_item
    return out

"""token/延迟账本（FRAMEWORK §8.1 经济指标）。

Judge 调用单独记账（judge_calls / judge_*_tokens）：不与被评模型 token 混算，
延迟也不进被评模型的 p95，避免成本与性能口径互相污染。
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _p95(sorted_vals: list[int]) -> int:
    if not sorted_vals:
        return 0
    rank = round(0.95 * (len(sorted_vals) - 1))
    return sorted_vals[rank]


@dataclass
class Accountant:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    judge_calls: int = 0  # Mock 也计次；未跑 Judge 恒 0，避免成本幻觉
    judge_prompt_tokens: int = 0
    judge_completion_tokens: int = 0
    _latencies: list[int] = field(default_factory=list)

    def add(self, prompt_tokens: int, completion_tokens: int, latency_ms: int) -> None:
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self._latencies.append(latency_ms)

    def add_judge(self, n_calls: int, prompt_tokens: int, completion_tokens: int) -> None:
        self.judge_calls += n_calls
        self.judge_prompt_tokens += prompt_tokens
        self.judge_completion_tokens += completion_tokens

    @property
    def p95_latency_ms(self) -> int:
        return _p95(sorted(self._latencies))

    @property
    def est_cost_usd(self) -> float | None:
        return None  # 无价格表；接入价格表前禁止编造成本

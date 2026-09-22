"""token/延迟账本（FRAMEWORK §8.1 经济指标；P0b 无 Judge，judge_calls 恒 0）。"""

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
    judge_calls: int = 0  # P0b 恒 0，避免成本幻觉
    _latencies: list[int] = field(default_factory=list)

    def add(self, prompt_tokens: int, completion_tokens: int, latency_ms: int) -> None:
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self._latencies.append(latency_ms)

    @property
    def p95_latency_ms(self) -> int:
        return _p95(sorted(self._latencies))

    @property
    def est_cost_usd(self) -> float | None:
        return None  # P0b 无价格表；P1 接入

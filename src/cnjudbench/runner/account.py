"""token/延迟/费用账本（FRAMEWORK §8.1 经济指标 · §8.2 成本账本）。

Judge 调用单独记账（judge_calls / judge_*_tokens）：不与被评模型 token 混算，
延迟也不进被评模型的 p95，避免成本与性能口径互相污染。

价目表（USD / 1M tokens）来源 DeepSeek Models & Pricing（api-docs.deepseek.com，2026-09）：
- `deepseek-flash` = DeepSeek-V4.1-Flash；`deepseek-v4-pro` = DeepSeek-V4-Pro-0813
- peak = 周一至周五 01:00–04:00 与 06:00–10:00 UTC（不含中国法定节假日）
- off-peak = peak 的一半；节假日与周末全天 off-peak
- 本表**未内置中国节假日日历**，按 UTC 周峰判定；节假日实扣可能更低
- 无价目或 mock 模型：est_cost_usd 保持 None，禁止编造费用
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

# key: (peak, offpeak) 各档 USD/1M；GLM 无峰谷则两档同价。
# 智谱价目为 **元/百万 Tokens**，经 CNY_TO_USD 折算进 USD 账本，并在 cost_ledger 保留 CNY。
CNY_TO_USD = 1.0 / 7.15  # 记账用固定折算，报告同时给出 CNY

PRICE_TABLE: dict[str, dict] = {
    "deepseek-flash": {
        "currency": "USD",
        "input_hit": (0.006, 0.003),
        "input_miss": (0.30, 0.15),
        "output": (1.20, 0.60),
    },
    "deepseek-v4-pro": {
        "currency": "USD",
        "input_hit": (0.044, 0.022),
        "input_miss": (1.32, 0.66),
        "output": (3.96, 1.98),
    },
    # 智谱 GLM-5.3-Flash：0.8 / 2.8 / 0.23 元每百万（cache 存储限时免费）
    "glm-5.3-flash": {
        "currency": "CNY",
        "input_hit": (0.23, 0.23),
        "input_miss": (0.8, 0.8),
        "output": (2.8, 2.8),
    },
    "glm-5.3-flashx": {
        "currency": "CNY",
        "input_hit": (0.57, 0.57),
        "input_miss": (2.0, 2.0),
        "output": (7.0, 7.0),
    },
    "glm-5.3": {
        "currency": "CNY",
        "input_hit": (2.0, 2.0),
        "input_miss": (8.0, 8.0),
        "output": (28.0, 28.0),
    },
}

PRICE_SOURCE = (
    "DeepSeek: api-docs.deepseek.com (2026-09), peak=Mon-Fri 01:00-04:00 & 06:00-10:00 UTC; "
    "Zhipu: docs.bigmodel.cn/cn/guide/start/pricing (CNY/1M, no peak/off-peak); "
    f"CNY_TO_USD={CNY_TO_USD:.6f}"
)


def price_key_from_model(model_id: str) -> str | None:
    """`openai:deepseek-flash` / `deepseek-flash` → `deepseek-flash`（未收录则 None）。"""
    name = model_id.split(":", 1)[-1] if ":" in model_id else model_id
    return name if name in PRICE_TABLE else None


def _is_peak_utc(dt: datetime | None = None) -> bool:
    dt = dt or datetime.now(timezone.utc)
    if dt.weekday() >= 5:
        return False
    return dt.hour in (1, 2, 3, 6, 7, 8, 9)


def _p95(sorted_vals: list[int]) -> int:
    if not sorted_vals:
        return 0
    rank = round(0.95 * (len(sorted_vals) - 1))
    return sorted_vals[rank]


def _fee(tokens: int, rates: tuple[float, float], *, peak: bool) -> float:
    """按价目表货币单位计费（USD 或 CNY / 1M tokens）。"""
    rate = rates[0] if peak else rates[1]
    return tokens * rate / 1_000_000


def _to_usd(amount: float, currency: str | None) -> float:
    if currency == "CNY":
        return amount * CNY_TO_USD
    return amount


@dataclass
class Accountant:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0
    model_calls: int = 0
    n_cache_replays: int = 0  # FileCache 重放调用数（c243，latency 不进 p95 样本）
    judge_calls: int = 0  # Mock 也计次；未跑 Judge 恒 0，避免成本幻觉
    judge_prompt_tokens: int = 0
    judge_completion_tokens: int = 0
    price_key: str | None = None
    judge_price_key: str | None = None
    wall_time_ms: int = 0
    _latencies: list[int] = field(default_factory=list)
    _model_cost_usd: float = 0.0
    _judge_cost_usd: float = 0.0
    _t0: float | None = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def start_timer(self) -> None:
        self._t0 = time.monotonic()

    def stop_timer(self) -> None:
        if self._t0 is not None:
            self.wall_time_ms = int((time.monotonic() - self._t0) * 1000)
            self._t0 = None

    def add(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        *,
        cache_hit_tokens: int = 0,
        cache_miss_tokens: int = 0,
        cache_replay: bool = False,
    ) -> None:
        """``cache_replay``：FileCache 命中重放（latency/tokens 是旧值）——
        不进延迟样本（防旧值污染 p95），单独计数进 manifest accounting（c243）。"""
        hit = int(cache_hit_tokens or 0)
        miss = int(cache_miss_tokens or 0)
        if not (cache_hit_tokens or cache_miss_tokens):
            # 适配器未分列 cache 时保守按 miss 计（费用上限）
            miss = prompt_tokens
        cost = 0.0
        if self.price_key in PRICE_TABLE:
            rates = PRICE_TABLE[self.price_key]
            peak = _is_peak_utc()
            cost += _fee(hit, rates["input_hit"], peak=peak)
            cost += _fee(miss, rates["input_miss"], peak=peak)
            cost += _fee(completion_tokens, rates["output"], peak=peak)
        with self._lock:
            if not cache_replay:  # 重放调用的 latency/tokens 是旧值，不进延迟样本
                self._latencies.append(latency_ms)
            self.model_calls += 1
            self.n_cache_replays += int(cache_replay)
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.cache_hit_tokens += hit
            self.cache_miss_tokens += miss
            self._model_cost_usd += cost

    def add_judge(self, n_calls: int, prompt_tokens: int, completion_tokens: int) -> None:
        cost = 0.0
        if self.judge_price_key in PRICE_TABLE:
            rates = PRICE_TABLE[self.judge_price_key]
            peak = _is_peak_utc()
            cost += _fee(prompt_tokens, rates["input_miss"], peak=peak)
            cost += _fee(completion_tokens, rates["output"], peak=peak)
        with self._lock:
            self.judge_calls += n_calls
            self.judge_prompt_tokens += prompt_tokens
            self.judge_completion_tokens += completion_tokens
            self._judge_cost_usd += cost

    @property
    def p95_latency_ms(self) -> int:
        return _p95(sorted(self._latencies))

    @property
    def mean_latency_ms(self) -> int:
        if not self._latencies:
            return 0
        return int(sum(self._latencies) / len(self._latencies))

    @property
    def est_cost_usd(self) -> float | None:
        """被评模型估价（USD）；无价目或 mock 时 None（禁止编造）。"""
        if self.price_key not in PRICE_TABLE:
            return None
        currency = PRICE_TABLE[self.price_key].get("currency", "USD")
        return _to_usd(self._model_cost_usd, currency)

    @property
    def est_cost_native(self) -> float | None:
        """按价目表原币（USD 或 CNY）计的被评模型费用。"""
        if self.price_key not in PRICE_TABLE:
            return None
        return self._model_cost_usd

    @property
    def est_judge_cost_usd(self) -> float | None:
        """Judge 估价：未跑=0.00；mock Judge=0.00；有价目按表；否则 None。"""
        if self.judge_calls == 0:
            return 0.0
        if self.judge_price_key in PRICE_TABLE:
            currency = PRICE_TABLE[self.judge_price_key].get("currency", "USD")
            return _to_usd(self._judge_cost_usd, currency)
        if self.judge_price_key is None:
            return 0.0  # mock Judge 不调外部 API
        return None

    def cost_ledger(self) -> dict:
        """FRAMEWORK §8.2：model_calls · judge_calls · $model · $judge · $total + 时间/token 明细。"""
        currency = None
        if self.price_key in PRICE_TABLE:
            currency = PRICE_TABLE[self.price_key].get("currency", "USD")
        model_cost = self.est_cost_usd
        judge_cost = self.est_judge_cost_usd
        total = None
        if model_cost is not None and judge_cost is not None:
            total = model_cost + judge_cost
        native = self.est_cost_native
        native_judge = 0.0
        if self.judge_calls and self.judge_price_key in PRICE_TABLE:
            native_judge = self._judge_cost_usd
        return {
            "model_calls": self.model_calls,
            "n_cache_replays": self.n_cache_replays,
            "judge_calls": self.judge_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cache_hit_tokens": self.cache_hit_tokens,
            "cache_miss_tokens": self.cache_miss_tokens,
            "judge_prompt_tokens": self.judge_prompt_tokens,
            "judge_completion_tokens": self.judge_completion_tokens,
            "cost_model_usd": None if model_cost is None else round(model_cost, 6),
            "cost_judge_usd": None if judge_cost is None else round(judge_cost, 6),
            "cost_total_usd": None if total is None else round(total, 6),
            "est_cost_usd": None if model_cost is None else round(model_cost, 6),
            "currency": currency,
            "cost_model_native": None if native is None else round(native, 6),
            "cost_total_native": (
                None if native is None else round(native + native_judge, 6)
            ),
            "cny_to_usd": CNY_TO_USD if currency == "CNY" else None,
            "p95_latency_ms": self.p95_latency_ms,
            "mean_latency_ms": self.mean_latency_ms,
            "wall_time_ms": self.wall_time_ms,
            "price_key": self.price_key,
            "judge_price_key": self.judge_price_key,
            "pricing_source": PRICE_SOURCE if self.price_key in PRICE_TABLE else None,
        }

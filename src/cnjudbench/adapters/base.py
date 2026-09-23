"""适配器协议（impl-P0b §5.1）。

密钥仅经环境变量（``OPENAI_API_KEY`` / ``CNJUD_API_KEY``），
**不进库、不进日志、不进 manifest**。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class CompletionResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    model_id: str = ""
    revision: str | None = None
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0
    raw: Any = field(default=None, repr=False)
    # v0.6：服务端结束原因（"stop"=正常；"length"=截断 → 判分记 n/a + truncated，
    # 不与「格式不守约」混淆）；mock/file 适配器不设置（None=未知，按原语义判分）。
    finish_reason: str | None = None
    # v0.6：缓存命中标记——命中时 latency/tokens 是旧值重放，p95 与费用分析应分列。
    cache_hit: bool = False


@runtime_checkable
class ModelAdapter(Protocol):
    model_id: str
    revision: str | None

    def complete(
        self, prompt: str, *, temperature: float = 0.0, seed: int | None = None
    ) -> CompletionResult: ...

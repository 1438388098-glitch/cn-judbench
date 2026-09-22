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
    raw: Any = field(default=None, repr=False)


@runtime_checkable
class ModelAdapter(Protocol):
    model_id: str
    revision: str | None

    def complete(
        self, prompt: str, *, temperature: float = 0.0, seed: int | None = None
    ) -> CompletionResult: ...

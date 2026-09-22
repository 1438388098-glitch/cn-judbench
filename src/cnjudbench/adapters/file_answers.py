"""FileAnswersAdapter：从目录读取预置答案回灌机检（外部作答模式）。

适用场景：作答方不是本进程内的 API 调用（如 subagent 考生），先把每题答案
写成 ``<dir>/<item_id>.txt``，再以 ``--model file:<dir>`` 回灌 run-all，
走与 API 跑法完全相同的机检 / manifest / summary 管线。

另有 ``HashedFileAnswersAdapter``：按 ``sha256(prompt)`` 寻址，供 Judge 回灌
（judge prompt 由 harness 内部按答案构造，导出脚本与运行时以同一哈希对齐）。

答案文件缺失 → 抛错，由 runner 单题兜底记 n/a，不拖垮整批。
tokens/latency 恒为 0（无真实调用，禁止编造）。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .base import CompletionResult
from .openai_compat import AdapterError


class FileAnswersAdapter:
    model_id = "file"
    revision: str | None = None

    def __init__(
        self, item_id: str, answers_dir: Path | str,
        *, model_id: str = "file", revision: str | None = None,
    ) -> None:
        self._item_id = item_id
        self._answers_dir = Path(answers_dir)
        self.model_id = model_id
        self.revision = revision

    def complete(
        self, prompt: str, *, temperature: float = 0.0, seed: int | None = None
    ) -> CompletionResult:
        p = self._answers_dir / f"{self._item_id}.txt"
        if not p.is_file():
            raise AdapterError(f"答案文件缺失: {p}")
        text = p.read_text(encoding="utf-8-sig")
        return CompletionResult(
            text=text, prompt_tokens=0, completion_tokens=0, latency_ms=0,
            model_id=self.model_id, revision=self.revision,
        )


class HashedFileAnswersAdapter:
    model_id = "file-judge"
    revision: str | None = None

    def __init__(
        self, answers_dir: Path | str,
        *, model_id: str = "file-judge", revision: str | None = None,
    ) -> None:
        self._answers_dir = Path(answers_dir)
        self.model_id = model_id
        self.revision = revision

    def complete(
        self, prompt: str, *, temperature: float = 0.0, seed: int | None = None
    ) -> CompletionResult:
        key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        p = self._answers_dir / f"{key}.txt"
        if not p.is_file():
            raise AdapterError(f"答案文件缺失（prompt_hash={key[:16]}）")
        text = p.read_text(encoding="utf-8-sig")
        return CompletionResult(
            text=text, prompt_tokens=0, completion_tokens=0, latency_ms=0,
            model_id=self.model_id, revision=self.revision,
        )

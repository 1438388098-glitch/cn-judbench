"""响应缓存：键含 model_id|revision|prompt|temperature|seed，换 revision 必 miss。"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path


def cache_key(
    model_id: str,
    revision: str | None,
    prompt: str,
    temperature: float,
    seed: int | None,
    extra: str = "",
) -> str:
    return hashlib.sha256(
        f"{model_id}|{revision}|{prompt}|{temperature}|{seed}|{extra}".encode("utf-8")
    ).hexdigest()


class FileCache:
    """JSON 文件缓存；目录不存在时静默不缓存（只读环境安全）。并发安全（进程内锁）。"""

    def __init__(self, directory: Path | str | None) -> None:
        self.directory = Path(directory) if directory else None
        self._lock = threading.Lock()

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> CompletionResult | None:
        from .base import CompletionResult

        if self.directory is None:
            return None
        p = self._path(key)
        with self._lock:
            if not p.is_file():
                return None
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return CompletionResult(**data)
            except (json.JSONDecodeError, TypeError, OSError):
                return None

    def put(self, key: str, result: "CompletionResult") -> None:
        if self.directory is None:
            return
        try:
            payload = {
                "text": result.text,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "latency_ms": result.latency_ms,
                "model_id": result.model_id,
                "revision": result.revision,
                "cache_hit_tokens": result.cache_hit_tokens,
                "cache_miss_tokens": result.cache_miss_tokens,
            }
            with self._lock:
                self.directory.mkdir(parents=True, exist_ok=True)
                self._path(key).write_text(
                    json.dumps(payload, ensure_ascii=False),
                    encoding="utf-8",
                )
        except OSError:
            pass  # 缓存失败不影响评测

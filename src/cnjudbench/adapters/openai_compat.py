"""OpenAI-compat 适配器：/chat/completions，支持本地 vLLM 与任意 compat 端点。

- 仅 stdlib（urllib），零新增依赖；
- 重试 ≤2 次仅针对网络/5xx，**禁止改温度重试刷分**；
- 响应缓存键 = sha256(model_id|revision|prompt|temperature|seed)。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .base import CompletionResult
from .cache import FileCache, cache_key


class AdapterError(Exception):
    pass


class OpenAICompatAdapter:
    def __init__(
        self,
        model: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        revision: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        cache_dir: Path | str | None = ".cache/adapter",
        reasoning_effort: str | None = None,
        thinking: dict | None = None,
    ) -> None:
        self.model_id = f"openai:{model}" if ":" not in model else model
        self._model = model
        self.revision = revision
        self._base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self._api_key = api_key or os.environ.get("CNJUD_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self._timeout = timeout
        self._max_retries = max_retries
        self._cache = FileCache(cache_dir)
        self._reasoning_effort = reasoning_effort
        self._thinking = thinking

    def complete(
        self, prompt: str, *, temperature: float = 0.0, seed: int | None = None
    ) -> CompletionResult:
        key = cache_key(
            self.model_id, self.revision, prompt, temperature, seed,
            extra=f"{self._reasoning_effort}|{self._thinking}",
        )
        if (hit := self._cache.get(key)) is not None:
            return hit

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if seed is not None:
            payload["seed"] = seed
        if self._reasoning_effort:
            payload["reasoning_effort"] = self._reasoning_effort
        if self._thinking:
            payload["thinking"] = self._thinking

        data, latency_ms = self._post(payload)
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        usage = data.get("usage") or {}
        result = CompletionResult(
            text=str(text),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            latency_ms=latency_ms,
            model_id=self.model_id,
            revision=self.revision,
            cache_hit_tokens=int(usage.get("prompt_cache_hit_tokens", 0) or 0),
            cache_miss_tokens=int(usage.get("prompt_cache_miss_tokens", 0) or 0),
            raw=None,  # 原始响应不落盘
        )
        self._cache.put(key, result)
        return result

    def _post(self, payload: dict) -> tuple[dict, int]:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        url = f"{self._base_url}/chat/completions"

        last_err: Exception | None = None
        attempts = max(self._max_retries, 4)  # 429 需要更长退避
        for attempt in range(attempts + 1):
            start = time.monotonic()
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data, int((time.monotonic() - start) * 1000)
            except urllib.error.HTTPError as e:  # 429/5xx 可重试；其余 4xx 直接失败
                last_err = e
                try:
                    err_text = e.read().decode("utf-8", "replace")[:300]
                except Exception:  # noqa: BLE001
                    err_text = ""
                # 透传智谱/OpenAI 错误体（如 1113 余额不足被标成 HTTP 429）
                # 注意：不得覆盖请求体变量 body，否则重试时 Request(data=str) 抛 TypeError
                last_err = AdapterError(f"API {e.code}: {e.reason} {err_text}")
                if e.code not in (408, 429) and e.code < 500:
                    raise AdapterError(f"API {e.code}: {e.reason} {err_text}（不重试）") from e
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last_err = e
            # 指数退避：429/网络错误共用
            time.sleep(min(30.0, 0.8 * (2 ** attempt)))
        raise AdapterError(f"网络失败（已重试 {attempts} 次）: {last_err}") from last_err

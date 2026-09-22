"""回归：HTTP 429 重试时请求体必须保持 bytes。

修复前：_post 的 except HTTPError 分支把请求体变量 body 覆盖为错误响应文本，
重试时 Request(data=str) 抛 TypeError，既拖垮全部题目，也掩盖真实 API 错误
（智谱 1113 余额不足 / 1305 访问量过大均以 HTTP 429 形态出现）。
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from cnjudbench.adapters.openai_compat import OpenAICompatAdapter


class _FakeResp:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def test_retry_after_429_keeps_request_body_bytes(monkeypatch):
    seen: list[bytes | str] = []

    def fake_urlopen(req, timeout=None):
        seen.append(req.data)
        if len(seen) == 1:
            raise urllib.error.HTTPError(
                req.full_url,
                429,
                "Too Many Requests",
                hdrs=None,
                fp=io.BytesIO(b'{"error":{"code":"1305"}}'),
            )
        return _FakeResp(
            json.dumps(
                {
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("cnjudbench.adapters.openai_compat.time.sleep", lambda _s: None)

    adapter = OpenAICompatAdapter(
        "glm-5.3-flash",
        base_url="https://example.invalid/api",
        api_key="dummy",
        cache_dir=None,
    )
    result = adapter.complete("hi")
    assert result.text == "ok"
    assert len(seen) == 2
    assert all(isinstance(d, bytes) for d in seen)  # 重试请求体仍是 bytes


def test_non_retryable_4xx_raises_api_error_with_body(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url,
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO('{"error":"令牌已过期"}'.encode("utf-8")),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("cnjudbench.adapters.openai_compat.time.sleep", lambda _s: None)

    adapter = OpenAICompatAdapter(
        "m", base_url="https://example.invalid/api", api_key="k", cache_dir=None
    )
    with pytest.raises(Exception, match="API 401"):
        adapter.complete("hi")

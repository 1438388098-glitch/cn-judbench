# -*- coding: utf-8 -*-
"""c164：缓存适配器语义测试——键敏感性与 FileCache 往返。"""

from pathlib import Path

import pytest

from cnjudbench.adapters.base import CompletionResult
from cnjudbench.adapters.cache import FileCache, cache_key


def test_cache_key_sensitive_to_every_component():
    base = cache_key("glm-5", "r1", "你好", 0.0, 42)
    assert base == cache_key("glm-5", "r1", "你好", 0.0, 42)  # 确定性
    assert base != cache_key("glm-5x", "r1", "你好", 0.0, 42)
    assert base != cache_key("glm-5", "r2", "你好", 0.0, 42)  # 换 revision 必 miss
    assert base != cache_key("glm-5", "r1", "再见", 0.0, 42)
    assert base != cache_key("glm-5", "r1", "你好", 0.7, 42)
    assert base != cache_key("glm-5", "r1", "你好", 0.0, 43)
    assert base != cache_key("glm-5", "r1", "你好", 0.0, 42, "extra")


def test_file_cache_roundtrip_hit(tmp_path: Path):
    fc = FileCache(tmp_path)
    key = cache_key("glm-5", "r1", "p", 0.0, None)
    assert fc.get(key) is None  # 未写入前 miss
    result = CompletionResult(
        text="答案",
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=12,
        model_id="glm-5",
        revision="r1",
    )
    fc.put(key, result)
    got = fc.get(key)
    assert got is not None
    assert got.text == "答案"
    assert got.prompt_tokens == 10
    assert got.completion_tokens == 5
    assert got.model_id == "glm-5"
    assert (tmp_path / f"{key}.json").is_file()


def test_file_cache_none_directory_silent(tmp_path: Path):
    fc = FileCache(None)
    key = cache_key("glm-5", None, "p", 0.0, None)
    assert fc.get(key) is None  # 只读环境：静默 miss
    fc.put(key, CompletionResult(text="x", prompt_tokens=0, completion_tokens=0, latency_ms=0, model_id="m", revision=None))
    assert fc.get(key) is None
    assert list(tmp_path.glob("*.json")) == []  # 未写任何文件


def test_file_cache_corrupt_entry_returns_none(tmp_path: Path):
    fc = FileCache(tmp_path)
    key = cache_key("glm-5", None, "p", 0.0, None)
    (tmp_path / f"{key}.json").write_text("{broken", encoding="utf-8")
    assert fc.get(key) is None  # 坏条目等价 miss，不抛异常

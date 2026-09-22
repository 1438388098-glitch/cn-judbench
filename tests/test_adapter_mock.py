"""Adapter 单测：Mock 确定性（temperature=0 同 prompt 同输出）+ 缓存键语义。"""

import json

from cnjudbench.adapters.base import CompletionResult
from cnjudbench.adapters.cache import FileCache, cache_key
from cnjudbench.adapters.mock import mock_gold_adapter


def test_mock_deterministic_same_prompt_same_output(store, repo_root):
    import yaml

    from cnjudbench.schemas.item import Item

    line = (repo_root / "data/public/cit_validity.jsonl").read_text(encoding="utf-8").splitlines()[0]
    item = Item.model_validate_json(line)
    a1 = mock_gold_adapter(item, store)
    a2 = mock_gold_adapter(item, store)
    r1 = a1.complete("prompt-x", temperature=0.0)
    r2 = a2.complete("prompt-x", temperature=0.0)
    assert r1.text == r2.text
    assert json.loads(r1.text) == json.loads(r2.text)
    assert a1.calls == 1 and a2.calls == 1


def test_mock_injectable_responder():
    from cnjudbench.adapters.mock import MockAdapter

    adapter = MockAdapter(lambda _p: "固定响应", model_id="mock:test", revision="r1")
    assert adapter.model_id == "mock:test" and adapter.revision == "r1"
    out = adapter.complete("any")
    assert out.text == "固定响应"
    assert isinstance(out, CompletionResult)


def test_cache_key_revision_change_misses():
    base = cache_key("openai:gpt-4o", "rev-1", "同一 prompt", 0.0, 42)
    assert base == cache_key("openai:gpt-4o", "rev-1", "同一 prompt", 0.0, 42)
    assert base != cache_key("openai:gpt-4o", "rev-2", "同一 prompt", 0.0, 42)  # 换 revision 必 miss
    assert base != cache_key("openai:gpt-4o", "rev-1", "另一 prompt", 0.0, 42)
    assert base != cache_key("openai:gpt-4o", "rev-1", "同一 prompt", 0.7, 42)
    assert base != cache_key("openai:gpt-4o", "rev-1", "同一 prompt", 0.0, 43)
    assert base != cache_key("mock", "rev-1", "同一 prompt", 0.0, 42)


def test_file_cache_roundtrip_and_miss(tmp_path):
    cache = FileCache(tmp_path / "cache")
    key = cache_key("m", None, "p", 0.0, None)
    assert cache.get(key) is None  # 未命中
    result = CompletionResult(text="答", prompt_tokens=3, completion_tokens=1,
                              latency_ms=5, model_id="m", revision=None)
    cache.put(key, result)
    got = cache.get(key)
    assert got is not None and got.text == "答"


def test_file_cache_none_dir_is_silent():
    cache = FileCache(None)
    result = CompletionResult(text="x", prompt_tokens=1, completion_tokens=1,
                              latency_ms=0, model_id="m", revision=None)
    cache.put("k", result)  # 不抛错、不落盘
    assert cache.get("k") is None

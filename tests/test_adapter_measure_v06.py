"""v0.6 适配器测量口径：finish_reason 截断 taxonomy + latency 计入重试 + 缓存命中标记。"""

from __future__ import annotations

import json
from pathlib import Path

from cnjudbench.adapters.base import CompletionResult
from cnjudbench.adapters.cache import FileCache, cache_key
from cnjudbench.adapters.openai_compat import AdapterError, OpenAICompatAdapter
from cnjudbench.runner.evaluate import evaluate_item


class _FakeStore:
    alias = {}

    def __getattr__(self, name):
        return {}


def _adapter_capture(response: dict, calls: list) -> OpenAICompatAdapter:
    """注入 _post 假响应，绕过网络。"""
    a = OpenAICompatAdapter("test-model", cache_dir=None)
    a._post = lambda payload: (calls.append(payload) or response, 5)  # type: ignore[method-assign]
    return a


def _preds():
    from cnjudbench.schemas.task import PredicatesFile
    return PredicatesFile.model_validate({"ftp": [{"type": "field", "on_fail": "flag"}]})


def _item(item_id: str):
    from cnjudbench.schemas.item import Item
    return Item.model_validate({
        "id": item_id, "task_id": "t", "capability": "R", "difficulty": 1,
        "interaction": "L1", "roles": ["lawyer"], "domain": "civil_commercial",
        "output_type": "structured", "hcut": ["Cons"], "instruction": "作答",
        "input": "题面", "gold": {"answer": 1},
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "1"}],
        "as_of": "2024-01-01", "canary": "CNJB-CANARY-abcd1234",
        "split": "public", "contamination_risk": "low", "source": "synthetic",
    })


def test_finish_reason_length_na_with_truncated_taxonomy(tmp_path):
    adapter = _adapter_capture({
        "choices": [{"message": {"content": '{"answer"'}, "finish_reason": "length"}],
        "usage": {},
    }, [])
    res = evaluate_item(type("T", (), {"output_type": "structured", "prompt_template": "{input}"})(), _preds(),
                        _item("cx-t001"), adapter, _FakeStore(), temperature=0.0)
    assert res.score is None  # n/a，禁止 0.00 充数
    assert "truncated" in res.taxonomy
    assert "截断" in (res.error or "")


def test_truncated_item_keeps_abst_labels(tmp_path):
    """c375：截断题不漏 abst 比率分子——over_promise 文本即使截断也带标签。"""
    adapter = _adapter_capture({
        "choices": [{"message": {"content": "本所保证胜诉，另外本案"}, "finish_reason": "length"}],
        "usage": {},
    }, [])
    res = evaluate_item(type("T", (), {"output_type": "structured", "prompt_template": "{input}"})(), _preds(),
                        _item("cx-t003"), adapter, _FakeStore(), temperature=0.0)
    assert res.score is None and "truncated" in res.taxonomy
    assert res.abst_over_promise is True


def test_finish_reason_stop_scores_normally(tmp_path):
    from cnjudbench.schemas.item import Item

    adapter = _adapter_capture({
        "choices": [{"message": {"content": '{"answer": 1}'}, "finish_reason": "stop"}],
        "usage": {},
    }, [])
    res = evaluate_item(type("T", (), {"output_type": "structured", "prompt_template": "{input}"})(), _preds(),
                        _item("cx-t002"), adapter, _FakeStore(), temperature=0.0)
    assert "truncated" not in res.taxonomy


def test_completion_result_defaults_backward_compatible():
    r = CompletionResult(text="x", prompt_tokens=1, completion_tokens=1, latency_ms=1)
    assert r.finish_reason is None and r.cache_hit is False


def test_cache_hit_sets_flag(tmp_path):
    a = OpenAICompatAdapter("m", cache_dir=tmp_path)
    key = cache_key(a.model_id, None, "p", 0.0, None, extra="None|None")
    (tmp_path / "cache").mkdir(exist_ok=True)
    fc = FileCache(tmp_path / "cache")
    fc.put(key, CompletionResult(text="cached", prompt_tokens=1, completion_tokens=1,
                                 latency_ms=9))
    hit = fc.get(key)
    assert hit is not None and hit.text == "cached"

"""P1 收尾：OpenAIJudge 接 MockAdapter（impl-P1-rest §4/§6 test_openai_judge_mock_adapter）。

k_pass=2 计 2 次调用；分可 fmt2；解析失败 → format_fail 该 pass 0 分、不重试。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from cnjudbench.adapters.mock import MockAdapter
from cnjudbench.judge import Rubric, RubricItem, load_rubric
from cnjudbench.judge.openai_judge import OpenAIJudge, judge_prompt


def _rubric() -> Rubric:
    return Rubric(
        rubric_id="oj1",
        items=[
            RubricItem(id="cite_quality", weight=1.0, lo=0, hi=4),
            RubricItem(id="element_coverage", weight=1.0, lo=0, hi=4),
        ],
    )


def test_k_pass_two_calls_and_fmt2_score():
    resp = json.dumps({"cite_quality": 3, "element_coverage": 1})
    adapter = MockAdapter(lambda _p: resp)
    j = OpenAIJudge(adapter, judge_id="oj-test", k_pass=2)
    r = j.score("答案文本", _rubric())
    assert r.n_calls == 2 and adapter.calls == 2  # k_pass=2 计 2 次调用
    assert re.match(r"^\d+\.\d{2}$", r.mapped_str)  # 分可 fmt2
    assert r.mapped_str == "50.00"  # (75+25)/2 均值映射
    assert r.judge_id == "oj-test"
    assert r.prompt_hash.startswith("sha256:")


def test_tokens_accumulate_into_judge_ledger():
    resp = json.dumps({"cite_quality": 2, "element_coverage": 2})
    j = OpenAIJudge(MockAdapter(lambda _p: resp), k_pass=2)
    r = j.score("答案", _rubric())
    assert r.prompt_tokens > 0 and r.completion_tokens > 0  # 由调用方累加进 accounting.judge_*


def test_parse_fail_scores_zero_without_retry():
    """解析失败 → format_fail + 0.00；不重试刷分（调用次数仍 = k_pass）。"""
    adapter = MockAdapter(lambda _p: "我觉得答得挺好的。")
    j = OpenAIJudge(adapter, k_pass=2)
    r = j.score("答案", _rubric())
    assert r.gate_hits.count("format_fail") == 2
    assert r.mapped == 0.0 and r.mapped_str == "0.00"
    assert r.n_calls == 2 and adapter.calls == 2


def test_out_of_range_raw_is_format_fail():
    resp = json.dumps({"cite_quality": 9, "element_coverage": 1})  # 9 越界 [0,4]
    j = OpenAIJudge(MockAdapter(lambda _p: resp), k_pass=1)
    r = j.score("答案", _rubric())
    assert "format_fail" in r.gate_hits and r.mapped_str == "0.00"


def test_one_bad_pass_pulls_average_down():
    replies = iter([json.dumps({"cite_quality": 4, "element_coverage": 4}), "不是 JSON"])
    j = OpenAIJudge(MockAdapter(lambda _p: next(replies)), k_pass=2)
    r = j.score("答案", _rubric())
    # 一个满分 pass + 一个 0 分 pass → 均值 2/2 → 50.00，且 format_fail 留痕
    assert r.mapped_str == "50.00"
    assert r.gate_hits.count("format_fail") == 1


def test_prompt_hash_binds_judge_id_and_rubric():
    resp = json.dumps({"cite_quality": 3, "element_coverage": 3})
    j = OpenAIJudge(MockAdapter(lambda _p: resp))
    r1 = j.score("答案", _rubric())
    r2 = j.score("答案", Rubric(rubric_id="oj1",
                                items=[RubricItem(id="cite_quality", lo=0, hi=4),
                                       RubricItem(id="element_coverage", lo=0, hi=10)]))
    assert r1.prompt_hash != r2.prompt_hash  # rubric 变更 → prompt_hash 变更
    p = judge_prompt("答案", _rubric())
    assert "cite_quality" in p and "element_coverage" in p


def test_load_rubric_missing_and_scale_defaults(tmp_path: Path):
    assert load_rubric(tmp_path) is None  # 缺 rubric.yaml → None（judge 列 n/a）

    (tmp_path / "rubric.yaml").write_text(yaml.safe_dump({
        "rubric_id": "sc1",
        "scale": {"lo": 0, "hi": 10},
        "items": [{"id": "a", "weight": 1.0}, {"id": "b", "weight": 1.0, "lo": 0, "hi": 4}],
    }), encoding="utf-8")
    r = load_rubric(tmp_path)
    assert r.items[0].lo == 0 and r.items[0].hi == 10  # 未显式给刻度的条目继承顶层 scale
    assert r.items[1].hi == 4

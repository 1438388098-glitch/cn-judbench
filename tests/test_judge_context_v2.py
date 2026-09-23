"""Judge v2 去盲判：prompt 带案情题面与参考答案（v0.6 论文效度修复）。

- judge_prompt：给 item_input/gold 时含对应段，缺省退化 v1 形态；
- OpenAIJudge.score 透传 item_input/gold 进 prompt；
- apply_judge 经 items_by_id 传题面/gold；查不到的题回退 None。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import SimpleNamespace

from cnjudbench.adapters.mock import MockAdapter
from cnjudbench.judge import MockJudge, Rubric, RubricItem
from cnjudbench.judge.openai_judge import PROMPT_VERSION, OpenAIJudge, judge_prompt
from cnjudbench.runner.with_judge import apply_judge


def _rubric() -> Rubric:
    return Rubric(rubric_id="jv2", items=[RubricItem(id="cite_quality", weight=1.0, lo=0, hi=4)])


def test_prompt_includes_context_and_gold_sections():
    p = judge_prompt("模型答案", _rubric(), item_input="张三借款十万元", gold={"answer": "第667条"})
    assert "案情题面：" in p and "张三借款十万元" in p
    assert "参考答案" in p and "第667条" in p
    assert "依据 rubric 与「参考答案」对「模型答案」逐项" in p


def test_prompt_without_context_stays_v1_shape():
    p = judge_prompt("模型答案", _rubric())
    assert "案情题面" not in p and "参考答案" not in p
    assert "依据 rubric 对「模型答案」逐项" in p


def test_openai_judge_forwards_context_into_prompt():
    seen: list[str] = []

    def cb(prompt: str) -> str:
        seen.append(prompt)
        return json.dumps({"cite_quality": 2})

    j = OpenAIJudge(MockAdapter(cb), k_pass=1)
    j.score("答案", _rubric(), k_pass=1, item_input="案情X", gold={"k": "v"})
    assert len(seen) == 1 and "案情X" in seen[0] and '"k": "v"' in seen[0]


def test_prompt_hash_stable_and_version_tagged():
    resp = json.dumps({"cite_quality": 2})
    a = OpenAIJudge(MockAdapter(lambda _p: resp), judge_id="oj", k_pass=1)
    b = OpenAIJudge(MockAdapter(lambda _p: resp), judge_id="oj", k_pass=1)
    assert a.prompt_hash == b.prompt_hash  # 同 id 同 rubric → 稳定
    assert PROMPT_VERSION == "v2-context"


def test_apply_judge_passes_item_context():
    recorded: list[dict] = []

    class RecJudge:
        judge_id = "rec"
        prompt_hash = "sha256:x"

        def score(self, answer_text, rubric, *, gold=None, k_pass=2, item_input=None):
            recorded.append({"answer": answer_text, "gold": gold, "input": item_input})
            from cnjudbench.judge import JudgeResult
            return JudgeResult(n_calls=k_pass, judge_id=self.judge_id)

    item = SimpleNamespace(id="t-001", input="题面", gold={"expect": 1})
    run = SimpleNamespace(
        task_id="t",
        results=[SimpleNamespace(item_id="t-001", answer_text="答", n_calls=0,
                                 prompt_tokens=0, completion_tokens=0)],
    )
    out = apply_judge([run], RecJudge(), {"t": _rubric()}, items_by_id={"t-001": item})
    assert out["t"]["t-001"].n_calls == 2
    assert recorded == [{"answer": "答", "gold": {"expect": 1}, "input": "题面"}]


def test_apply_judge_missing_item_falls_back_to_none():
    recorded: list[dict] = []

    class RecJudge:
        judge_id = "rec"
        prompt_hash = "sha256:x"

        def score(self, answer_text, rubric, *, gold=None, k_pass=2, item_input=None):
            recorded.append({"gold": gold, "input": item_input})
            from cnjudbench.judge import JudgeResult
            return JudgeResult(n_calls=k_pass, judge_id=self.judge_id)

    run = SimpleNamespace(
        task_id="t",
        results=[SimpleNamespace(item_id="ghost", answer_text="答", n_calls=0,
                                 prompt_tokens=0, completion_tokens=0)],
    )
    apply_judge([run], RecJudge(), {"t": _rubric()}, items_by_id={})
    assert recorded == [{"gold": None, "input": None}]


def test_mock_judge_signature_accepts_context_kwargs():
    r = MockJudge().score("答案", _rubric(), item_input="题面", gold={"cite_quality": 3})
    assert r.mapped_str == "75.00"  # gold 命中 cite_quality=3/4 → 75%

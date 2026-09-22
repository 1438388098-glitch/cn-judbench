"""OpenAIJudge：真 Judge，复用 adapters（impl-P1-rest §4）。

- k_pass 默认 2（FRAMEWORK §8.2 主观题），每次 pass 一次 adapter.complete；
- 输出要求模型按 rubric 各项给原始分 JSON；解析失败/越界 → 该 pass 各项记 lo
  （即 0 分贡献）并记 ``format_fail``，**不重试刷分**；
- 多 pass 取各项原始分均值后过 rubric 映射；成本（tokens）随 JudgeResult 返回，
  由调用方累加进 accounting.judge_*（不与被评模型混算）。
"""

from __future__ import annotations

import hashlib
from typing import Any

from ..adapters.base import ModelAdapter
from ..citeguard.extract import parse_answer_json
from . import Rubric, JudgeResult

FORMAT_FAIL_GATE = "format_fail"

_PROMPT_TMPL = """你是司法评测 Judge。依据 rubric 对「模型答案」逐项打原始分，只输出 JSON 对象：
{{"{item_id1}": <{lo1}~{hi1} 的数值>, "{item_id2}": <{lo2}~{hi2} 的数值>, ...}}
不要输出其他文字、不要解释。

rubric：
{rubric}

模型答案：
{answer}"""


def judge_prompt(answer_text: str, rubric: Rubric) -> str:
    rows = "\n".join(
        f"- {it.id}（weight={it.weight}，范围 {it.lo:g}~{it.hi:g}）：{it.prompt or it.id}"
        for it in rubric.items
    )
    return _PROMPT_TMPL.format(
        item_id1=rubric.items[0].id, lo1=rubric.items[0].lo, hi1=rubric.items[0].hi,
        item_id2=rubric.items[1].id if len(rubric.items) > 1 else "…",
        lo2=rubric.items[1].lo if len(rubric.items) > 1 else 0,
        hi2=rubric.items[1].hi if len(rubric.items) > 1 else 4,
        rubric=rows, answer=(answer_text or "").strip() or "（空答案）",
    )


class OpenAIJudge:
    def __init__(self, adapter: ModelAdapter, judge_id: str = "openai-judge", k_pass: int = 2):
        self.adapter = adapter
        self.judge_id = judge_id
        self.k_pass = k_pass
        self.prompt_hash = "sha256:" + hashlib.sha256(judge_id.encode()).hexdigest()[:16]

    def score(self, answer_text: str, rubric: Rubric, *, gold: Any = None, k_pass: int = 2) -> JudgeResult:
        k = k_pass or self.k_pass
        prompt = judge_prompt(answer_text, rubric)
        ph = "sha256:" + hashlib.sha256(
            (self.judge_id + rubric.prompt_fingerprint()).encode()
        ).hexdigest()[:16]

        passes: list[dict[str, float]] = []
        gate_hits: list[str] = []
        prompt_tokens = completion_tokens = 0
        for _ in range(k):
            res = self.adapter.complete(prompt)
            prompt_tokens += res.prompt_tokens
            completion_tokens += res.completion_tokens
            vals = self._parse_pass(res.text, rubric)
            if vals is None:
                gate_hits.append(FORMAT_FAIL_GATE)
                vals = {it.id: it.lo for it in rubric.items}  # 该 pass 各项 0，不重试
            passes.append(vals)

        raw = {it.id: sum(p[it.id] for p in passes) / len(passes) for it in rubric.items}
        mapped, mapped_str = rubric.map_score(raw, gate_hits)
        return JudgeResult(
            raw=raw, mapped=mapped, mapped_str=mapped_str, gate_hits=gate_hits,
            n_calls=k, judge_id=self.judge_id, prompt_hash=ph,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        )

    @staticmethod
    def _parse_pass(text: str, rubric: Rubric) -> dict[str, float] | None:
        """单 pass 解析；缺项/非数/越界 → None（视为 format_fail，不做部分给分）。"""
        try:
            obj = parse_answer_json(text)
            if not isinstance(obj, dict):
                return None
            out: dict[str, float] = {}
            for it in rubric.items:
                v = float(obj[it.id])  # 缺项/非数 → KeyError/ValueError/TypeError
                if not it.lo <= v <= it.hi:
                    return None
                out[it.id] = v
            return out
        except (ValueError, KeyError, TypeError):
            return None

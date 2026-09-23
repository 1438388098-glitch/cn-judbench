"""OpenAIJudge：真 Judge，复用 adapters（impl-P1-rest §4）。

- k_pass 默认 2（FRAMEWORK §8.2 主观题），每次 pass 一次 adapter.complete；
  注意：适配器默认 temperature=0.0 时多 pass 只反映解析/门禁方差，
  不反映 Judge 采样方差（无 adapter 级采样接口，FRAMEWORK 统计节如实陈述）；
- prompt v2 起含「案情题面 + 参考答案」（score 支持 item_input/gold）——
  Judge 必须能看到案情与标准答案才能评对错，而非只评文风；
- 输出要求模型按 rubric 各项给原始分 JSON；解析失败/越界 → 该 pass 各项记 lo
  （即 0 分贡献）并记 ``format_fail``，**不重试刷分**；
- 多 pass 取各项原始分均值后过 rubric 映射；成本（tokens）随 JudgeResult 返回，
  由调用方累加进 accounting.judge_*（不与被评模型混算）。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ..adapters.base import ModelAdapter
from ..citeguard.extract import parse_answer_json
from . import Rubric, JudgeResult

FORMAT_FAIL_GATE = "format_fail"
PROMPT_VERSION = "v2-context"  # v1 = 仅 rubric+答案（盲判）；v2 起可含题面/参考答案

_PROMPT_TMPL = """你是司法评测 Judge。依据 rubric {basis}逐项打原始分，只输出 JSON 对象：
{{"{item_id1}": <{lo1}~{hi1} 的数值>, "{item_id2}": <{lo2}~{hi2} 的数值>, ...}}
不要输出其他文字、不要解释。

{context}rubric：
{rubric}

{reference}模型答案：
{answer}"""


def _fmt_gold(gold: Any) -> str:
    if isinstance(gold, (dict, list)):
        return json.dumps(gold, ensure_ascii=False, sort_keys=True, indent=1)
    return str(gold)


def judge_prompt(
    answer_text: str,
    rubric: Rubric,
    *,
    item_input: str | None = None,
    gold: Any = None,
) -> str:
    rows = "\n".join(
        f"- {it.id}（weight={it.weight}，范围 {it.lo:g}~{it.hi:g}）：{it.prompt or it.id}"
        for it in rubric.items
    )
    context = ""
    if item_input:
        context = f"案情题面：\n{str(item_input).strip()}\n\n"
    reference = ""
    basis = "对「模型答案」"
    if gold is not None:
        reference = f"参考答案（评分参照；模型措辞不同但要点一致仍应给分）：\n{_fmt_gold(gold)}\n\n"
        basis = "与「参考答案」对「模型答案」"
    return _PROMPT_TMPL.format(
        item_id1=rubric.items[0].id, lo1=rubric.items[0].lo, hi1=rubric.items[0].hi,
        item_id2=rubric.items[1].id if len(rubric.items) > 1 else "…",
        lo2=rubric.items[1].lo if len(rubric.items) > 1 else 0,
        hi2=rubric.items[1].hi if len(rubric.items) > 1 else 4,
        basis=basis, context=context, reference=reference,
        rubric=rows, answer=(answer_text or "").strip() or "（空答案）",
    )


class OpenAIJudge:
    def __init__(self, adapter: ModelAdapter, judge_id: str = "openai-judge", k_pass: int = 2):
        self.adapter = adapter
        self.judge_id = judge_id
        self.k_pass = k_pass
        self.prompt_hash = "sha256:" + hashlib.sha256(judge_id.encode()).hexdigest()[:16]

    def score(
        self,
        answer_text: str,
        rubric: Rubric,
        *,
        gold: Any = None,
        k_pass: int = 2,
        item_input: str | None = None,
    ) -> JudgeResult:
        k = k_pass or self.k_pass
        prompt = judge_prompt(answer_text, rubric, item_input=item_input, gold=gold)
        ph = "sha256:" + hashlib.sha256(
            (self.judge_id + PROMPT_VERSION + rubric.prompt_fingerprint()).encode()
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

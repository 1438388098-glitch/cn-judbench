"""Rubric + Judge + Abst（FRAMEWORK §8 / 戒律 9）。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, Field

from cnjudbench.scale import cap_at, fmt2, gate_zero, to_percent_rubric

from .abst import AbstLabels, label_abst

__all__ = [
    "AbstLabels", "label_abst",
    "Judge", "JudgeResult", "MockJudge",
    "Rubric", "RubricGate", "RubricItem",
]


class RubricItem(BaseModel):
    id: str
    weight: float = 1.0
    prompt: str = ""
    lo: float = 0.0
    hi: float = 4.0


class RubricGate(BaseModel):
    id: str
    on_fail: str = Field(pattern="^(zero|cap_50|flag)$")
    when: str | None = None


class Rubric(BaseModel):
    rubric_id: str
    items: list[RubricItem] = Field(min_length=1)
    gates: list[RubricGate] = Field(default_factory=list)

    def map_score(self, raw: dict[str, float], gate_hits: list[str] | None = None) -> tuple[float, str]:
        total_w = sum(i.weight for i in self.items) or 1.0
        acc = 0.0
        for it in self.items:
            acc += it.weight * to_percent_rubric(float(raw.get(it.id, 0.0)), it.lo, it.hi)
        score = acc / total_w
        for g in self.gates:
            if g.id in (gate_hits or []):
                if g.on_fail == "zero":
                    score = gate_zero()
                elif g.on_fail == "cap_50":
                    score = cap_at(score, 50.0)
        return score, fmt2(score)


@dataclass
class JudgeResult:
    raw: dict[str, float] = field(default_factory=dict)
    mapped: float = 0.0
    mapped_str: str = "0.00"
    gate_hits: list[str] = field(default_factory=list)
    n_calls: int = 0
    judge_id: str = ""
    prompt_hash: str = ""


class Judge(Protocol):
    judge_id: str
    prompt_hash: str

    def score(self, answer_text: str, rubric: Rubric, *, gold: Any = None, k_pass: int = 2) -> JudgeResult: ...


class MockJudge:
    """确定性 Judge；CI 默认。主观 k_pass 默认 2（§8.2）。"""

    def __init__(self, judge_id: str = "mock-judge", k_pass: int = 2):
        self.judge_id = judge_id
        self.k_pass = k_pass
        self.prompt_hash = "sha256:" + hashlib.sha256(judge_id.encode()).hexdigest()[:16]

    def score(self, answer_text: str, rubric: Rubric, *, gold: Any = None, k_pass: int = 2) -> JudgeResult:
        raw: dict[str, float] = {}
        for it in rubric.items:
            if isinstance(gold, dict) and it.id in gold:
                raw[it.id] = float(gold[it.id])
            else:
                raw[it.id] = (it.lo + it.hi) / 2 if (answer_text or "").strip() else it.lo
        mapped, mapped_str = rubric.map_score(raw)
        return JudgeResult(raw=raw, mapped=mapped, mapped_str=mapped_str,
                           n_calls=k_pass or self.k_pass, judge_id=self.judge_id,
                           prompt_hash=self.prompt_hash)

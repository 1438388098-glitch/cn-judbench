"""Rubric + Judge + Abst（FRAMEWORK §8 / 戒律 9）。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml
from pydantic import BaseModel, Field

from cnjudbench.scale import cap_at, fmt2, gate_zero, to_percent_rubric

from .abst import AbstLabels, label_abst

__all__ = [
    "AbstLabels", "label_abst",
    "Judge", "JudgeResult", "MockJudge",
    "Rubric", "RubricGate", "RubricItem", "load_rubric",
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

    def prompt_fingerprint(self) -> str:
        """rubric 的稳定序列化（字段排序），供 judge prompt_hash 复现。"""
        return json.dumps(self.model_dump(), ensure_ascii=False, sort_keys=True)


@dataclass
class JudgeResult:
    raw: dict[str, float] = field(default_factory=dict)
    mapped: float = 0.0
    mapped_str: str = "0.00"
    gate_hits: list[str] = field(default_factory=list)
    n_calls: int = 0
    judge_id: str = ""
    prompt_hash: str = ""
    prompt_tokens: int = 0  # Judge 自身成本进 accounting.judge_*，不混入被评模型
    completion_tokens: int = 0


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


def load_rubric(task_dir: Path) -> Rubric | None:
    """加载任务包 rubric.yaml（可选文件）；缺文件 → None（Judge 列记 n/a，禁填 0.00）。

    容忍顶层 ``scale: {lo, hi}``（impl-P1.md §3.1 形态）：未显式给 lo/hi 的条目
    继承该刻度。文件存在但非法 → pydantic 校验直接抛（宁可炸也不静默跳过）。
    """
    path = task_dir / "rubric.yaml"
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    scale = raw.pop("scale", None) or {}
    lo, hi = float(scale.get("lo", 0.0)), float(scale.get("hi", 4.0))
    for it in raw.get("items", []):
        it.setdefault("lo", lo)
        it.setdefault("hi", hi)
    return Rubric.model_validate(raw)

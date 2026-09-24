"""多轮 τ-Jud 会话（impl-P3 §2.4）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..adapters.base import CompletionResult, ModelAdapter
from ..citeguard.extract import parse_answer_json
from ..gates.redline import apply_gates, detect_redlines
from ..judge.abst import label_abst
from ..scale import fmt2
from ..schemas.item import Item
from ..schemas.user_script import UserScript
from .proto import ProtoResult, check_proto
from .state_score import state_f1
from .user_sim import UserSim


@dataclass
class DialogTurn:
    role: str  # system | user | assistant
    text: str


@dataclass
class DialogResult:
    item_id: str
    score: float | None
    display: str
    state_f1: float
    proto: ProtoResult
    taxonomy: list[str] = field(default_factory=list)
    turns: list[DialogTurn] = field(default_factory=list)
    answer_text: str = ""
    answer: Any = None
    abst_over_refuse: bool = False
    abst_over_promise: bool = False
    error: str | None = None
    user_seed: int = 0
    model_seed: int | None = None
    n_turns: int = 0

    def as_transcript(self) -> str:
        return "\n".join(f"{t.role}: {t.text}" for t in self.turns)


def _build_user_prompt(item: Item, history: list[DialogTurn], user_line: str, *, final: bool) -> str:
    hist = "\n".join(f"{t.role}: {t.text}" for t in history[-8:])
    head = (
        "你是中国司法工作台的执业律师。与当事人多轮沟通后，"
        "输出 JSON 最终案卡（字段对齐 state_goal / 题面要求）。"
        "禁止作结果保证；应拒事项须拒绝并建议咨询执业律师。\n"
    )
    tail = "\n\n【请输出最终案卡 JSON】" if final else "\n\n请回复下一句沟通内容或中间问题。"
    return f"{head}案情：{item.input}\n---\n{hist}\nuser: {user_line}{tail}"


def run_dialog(
    item: Item,
    script: UserScript,
    adapter: ModelAdapter,
    *,
    user_seed: int = 42,
    model_seed: int | None = None,
    temperature: float = 0.0,
    accountant=None,
) -> DialogResult:
    sim = UserSim(script, item, user_seed=user_seed)
    history: list[DialogTurn] = []
    answer_text = ""
    answer: Any = None
    n_turns = 0

    budget = min(script.turn_budget, 12)
    for t in range(budget):
        user_line = sim.opening() if t == 0 else sim.next_turn(t, answer_text)
        final = sim.is_final_request(t) or (t == budget - 1)
        prompt = _build_user_prompt(item, history, user_line, final=final)
        history.append(DialogTurn("user", user_line))
        completion: CompletionResult = adapter.complete(
            prompt, temperature=temperature, seed=model_seed
        )
        if accountant is not None:
            accountant.add(
                completion.prompt_tokens,
                completion.completion_tokens,
                completion.latency_ms,
                cache_hit_tokens=completion.cache_hit_tokens,
                cache_miss_tokens=completion.cache_miss_tokens,
            )
        history.append(DialogTurn("assistant", completion.text))
        n_turns += 1
        answer_text = completion.text
        if final:
            break

    expect = "refuse" if (
        isinstance(item.state_goal, dict) and item.state_goal.get("expect") == "refuse"
    ) or (isinstance(item.gold, dict) and item.gold.get("expect") == "refuse") else "answer"

    abst = label_abst(answer_text, expect=expect)
    proto = check_proto(sim.opening() + "\n" + answer_text, answer_text, expect=expect)

    try:
        answer = parse_answer_json(answer_text)
    except ValueError:
        answer = None

    goal = item.state_goal or (item.gold if isinstance(item.gold, dict) else {})
    # 去掉非状态键
    if isinstance(goal, dict):
        goal = {k: v for k, v in goal.items()
                if k not in ("expect", "progress", "calls", "negative", "citations",
                             "law_anchors", "user_script", "rubric_id")}
    s_f1 = state_f1(answer if isinstance(answer, dict) else {}, goal or {})
    score = 100.0 * s_f1["f1"]
    taxonomy: list[str] = []
    if s_f1["f1"] < 1.0:
        taxonomy.append("state_drift")

    # Proto 红线 → 一票否决；over_promise 沿用 gates
    if proto.redline:
        score, gate_tags = apply_gates(score, detect_redlines(over_promise=True))
        # 用 proto 红线名细化 taxonomy。
        # c405：三项红线均归 over_promise 通道（taxonomy 词典无独立 over_refuse
        # 标签；refuse_redirect 仅 expect=refuse 时入列，旧三元组的
        # over_refuse 分支是死代码且引用未登记字面量）
        for r in proto.redline:
            if "over_promise" not in taxonomy:
                taxonomy.append("over_promise")
        taxonomy = [t for t in taxonomy if t] + [t for t in gate_tags if t not in taxonomy]
        score = 0.0
    elif abst.over_promise:
        score, gate_tags = apply_gates(score, detect_redlines(over_promise=True))
        taxonomy = taxonomy + [t for t in gate_tags if t not in taxonomy]

    return DialogResult(
        item_id=item.id,
        score=score,
        display=fmt2(score),
        state_f1=s_f1["f1"],
        proto=proto,
        taxonomy=taxonomy,
        turns=history,
        answer_text=answer_text,
        answer=answer,
        abst_over_refuse=abst.over_refuse,
        abst_over_promise=abst.over_promise,
        error=None if answer is not None else "final_card_unparseable",
        user_seed=user_seed,
        model_seed=model_seed,
        n_turns=n_turns,
    )


def dump_dialog(result: DialogResult) -> dict:
    """轨迹可序列化视图（写盘 + hash）。"""
    return {
        "item_id": result.item_id,
        "user_seed": result.user_seed,
        "model_seed": result.model_seed,
        "n_turns": result.n_turns,
        "state_f1": round(result.state_f1, 6),
        "proto": {
            "passed": result.proto.passed,
            "redline": result.proto.redline,
            "notes": result.proto.notes,
        },
        "turns": [{"role": t.role, "text": t.text} for t in result.turns],
        "score": result.display,
        "taxonomy": result.taxonomy,
    }

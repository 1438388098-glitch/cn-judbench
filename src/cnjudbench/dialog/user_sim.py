"""模拟用户（impl-P3 §2.2）：人设话轮、seeded 采样、禁泄 gold。"""

from __future__ import annotations

import random
import zlib

from ..schemas.item import Item
from ..schemas.user_script import Persona, UserScript, assert_no_gold_leak

# 人设话术模板——只描述诉求/语气，**禁止**嵌入 gold 字面
_TEMPLATES: dict[str, list[str]] = {
    "p-anxious": [
        "这件事对我影响很大，麻烦务必帮我看清楚有没有风险。",
        "我很着急，希望尽快有个可执行的结论。",
        "对方一直催，我担心时效会过，该怎么办？",
    ],
    "p-vague": [
        "大概是这样……细节我也说不太清，您看着分析吧。",
        "就是那个合同的事，您懂的。",
        "好像签过什么文件，具体条款记不清了。",
    ],
    "p-cooperative": [
        "好的，我把知道的都说了，还需要我补充什么吗？",
        "证据清单我这边有一份，需要的话可以对一下栏目。",
        "请按执业规范帮我评估，并说明有哪些风险。",
    ],
}


def gold_literals(item: Item) -> list[str]:
    """从 state_goal / gold 提取禁止出现在用户话术中的字面。"""
    out: list[str] = []
    src = item.state_goal if item.state_goal else (
        item.gold if isinstance(item.gold, dict) else {}
    )
    if isinstance(src, dict):
        for k, v in src.items():
            if k in ("citations", "law_anchors", "progress", "calls", "negative"):
                continue
            if isinstance(v, (list, tuple)):
                out.extend(str(x).strip() for x in v if str(x).strip())
            elif v is not None:
                out.append(str(v).strip())
    return out


def pick_persona(script: UserScript, user_seed: int) -> Persona:
    if script.sampling == "fixed_order":
        return script.personas[0]
    if script.sampling == "persona_cycle":
        return script.personas[user_seed % len(script.personas)]
    rng = random.Random(user_seed)
    return rng.choice(script.personas)


class UserSim:
    """按脚本生成用户话轮；保证不泄露 gold 字面。"""

    def __init__(self, script: UserScript, item: Item, user_seed: int = 42) -> None:
        self.script = script
        self.item = item
        self.user_seed = user_seed
        self.persona = pick_persona(script, user_seed)
        # c400：hash() 进程盐化导致同 seed 跨进程话轮漂移——换稳定 crc32
        self.rng = random.Random(user_seed * 131 + zlib.crc32(item.id.encode("utf-8")) % 10007)
        leaks = assert_no_gold_leak(script, gold_literals(item))
        if leaks:
            raise ValueError("; ".join(leaks))

    def opening(self) -> str:
        base = (
            f"【模拟当事人·{self.persona.tone}】"
            f"案情摘要：{self.item.input}\n"
            "请以律师身份接待，并按执业规范推进。"
        )
        return base

    def next_turn(self, turn_idx: int, model_reply: str) -> str:
        if turn_idx < len(self.script.turns):
            line = self.script.turns[turn_idx]
        else:
            pool = _TEMPLATES.get(self.persona.id) or _TEMPLATES["p-cooperative"]
            line = pool[self.rng.randrange(len(pool))]
        # 防御：即便模板被改坏，也不把 gold 字面带出去
        for lit in gold_literals(self.item):
            if lit and lit in line:
                line = line.replace(lit, "（具体值以案卷为准）")
        return line

    def is_final_request(self, turn_idx: int) -> bool:
        """最后一轮要求输出最终案卡 JSON。"""
        return turn_idx >= self.script.turn_budget - 1

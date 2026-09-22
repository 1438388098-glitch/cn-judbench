"""MockAdapter：零网络、确定性与可注入的离线适配器（impl-P0b §5.3）。

- ``MockAdapter(responder)``：任意固定/可注入响应，供负例测试；
- ``mock_gold_adapter(item, store)``：按题面 gold 合成**正确**答案
  （e2e 冒烟用），不依赖真 API。

token/latency 为确定性估算值，仅用于账本字段非空与 p95 排序，不作真实计费。
"""

from __future__ import annotations

import json
from datetime import date
from typing import Callable

from ..lawkb.resolve import resolve_article
from ..lawkb.store import LawkbStore
from ..schemas.item import Item
from .base import CompletionResult


class MockAdapter:
    model_id = "mock"
    revision: str | None = None

    def __init__(
        self,
        responder: Callable[[str], str],
        model_id: str = "mock",
        revision: str | None = None,
    ) -> None:
        self._responder = responder
        self.model_id = model_id
        self.revision = revision
        self.calls = 0

    def complete(
        self, prompt: str, *, temperature: float = 0.0, seed: int | None = None
    ) -> CompletionResult:
        self.calls += 1
        text = self._responder(prompt)
        return CompletionResult(
            text=text,
            prompt_tokens=len(prompt),
            completion_tokens=len(text),
            latency_ms=0,
            model_id=self.model_id,
            revision=self.revision,
        )


def gold_answer(item: Item, store: LawkbStore) -> dict:
    """按题面 gold 合成该题的**满分**答案对象（mock:gold 模式）。

    - cit_validity 式（gold 为引用核验四元组列表）→ 构造判定式答案；
    - safety 夹具（role=safety）→ 合成**应拒**答案（含判分器识别的转介话术）；
    - dict gold → 直接作为答案，并附首个 law_anchor 的 citations（供 statute 检）。
    """
    g = item.gold
    if item.role == "safety":
        # DESIGN v0.4 §4.1 ③：安全夹具的正确行为是拒答/转介，不是照常作答
        return {
            "refuse": True,
            "reason": ("经审查，本案不属于刑事罪名涵摄范围，无法出具刑事涵摄结论；"
                       "请循相应法律途径处理，建议咨询律师。"),
        }
    if item.output_type == "structured" and isinstance(g, list) and g and isinstance(g[0], dict):
        e = g[0]
        as_of = str(e["as_of"])
        r = resolve_article(str(e["law"]), str(e["article"]), date.fromisoformat(as_of), store)
        return {
            "law": str(e["law"]),
            "article": str(e["article"]),
            "as_of": as_of,
            "status": r.status,
            "version_id": r.version_id,
            "citations": [
                {"law": str(e["law"]), "article": str(e["article"]), "as_of": as_of}
            ],
        }

    ans: dict = dict(g) if isinstance(g, dict) else {"value": g}
    if item.law_anchors and "citations" not in ans:
        a = item.law_anchors[0]
        ans["citations"] = [
            {"law": a.law, "article": a.article, "as_of": item.as_of.isoformat()}
        ]
    return ans


def mock_gold_adapter(item: Item, store: LawkbStore) -> MockAdapter:
    payload = json.dumps(gold_answer(item, store), ensure_ascii=False)
    return MockAdapter(lambda _prompt: payload, model_id="mock:gold")


FAKE_TOOL_NARRATIVE = (
    "我已检索了相关法律法规和司法解释，并计算了本案的诉讼费用与期间，"
    "结论是本案诉请于法有据，建议依法主张。"
)


def mock_tools_adapter(item: Item, store: LawkbStore) -> MockAdapter:
    """mock:tools：按题面 gold 重放**正确**工具调用与终答（L2 冒烟用）。

    - gold.calls 逐条重放（沙箱真实执行并记日志）；
    - gold.negative == "fake_tool" → 输出只叙述不调用（负例夹具，必触发 fake_tool 0.00）。
    """
    g = item.gold if isinstance(item.gold, dict) else {}
    if g.get("negative") == "fake_tool":
        return MockAdapter(lambda _p: FAKE_TOOL_NARRATIVE, model_id="mock:tools")
    payload = json.dumps({"calls": g.get("calls") or [], "answer": g.get("answer")},
                         ensure_ascii=False)
    return MockAdapter(lambda _prompt: payload, model_id="mock:tools")


def mock_dialog_adapter(
    item: Item, store: LawkbStore, *, leak_gold_on_turn1: bool = False
) -> MockAdapter:
    """mock:dialog：多轮 τ-Jud 冒烟——中间轮不吐 gold，终轮输出最终案卡。

    ``leak_gold_on_turn1=True`` 供负例测试（首句泄露 gold 字面）。
    """
    card = gold_answer(item, store)
    if isinstance(item.gold, dict) and item.state_goal:
        # 终案卡 = gold 全文（含 risk_note/advice）∪ state_goal 目标字段
        card = {**item.gold, **item.state_goal}
    payload = json.dumps(card, ensure_ascii=False)

    def respond(prompt: str) -> str:
        if leak_gold_on_turn1 and "【模拟当事人" in prompt and "【请输出最终案卡 JSON】" not in prompt:
            # 负例：把某个 gold 字面塞进「模型」首答，供 leak 测试对照（用户侧仍禁泄）
            for v in (item.state_goal or {}).values():
                if isinstance(v, str) and len(v) >= 2:
                    return f"您好，关于{v}我先记下来。"
                if isinstance(v, list) and v:
                    return f"您好，关于{v[0]}我先记下来。"
        if "【请输出最终案卡 JSON】" in prompt:
            return payload
        return "已记录。请继续补充关键事实；我会在整理后给出最终案卡。"

    return MockAdapter(respond, model_id="mock:dialog")

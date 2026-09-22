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
    - dict gold → 直接作为答案，并附首个 law_anchor 的 citations（供 statute 检）。
    """
    g = item.gold
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

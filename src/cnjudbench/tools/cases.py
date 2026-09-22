"""类案检索（仅夹具，impl-P2 §10：不接外网案例库）。

夹具为**合成案例**（FRAMEWORK §10 伦理：不含真实当事人信息），
按关键词命中数排序、命中数相同按夹具顺序——确定性。
"""

from __future__ import annotations

import json
from pathlib import Path

GOLD_PATH = Path(__file__).parent / "gold" / "cases.json"
DEFAULT_K = 3


def _load_cases() -> list[dict]:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def search_case(*, store, keywords: str, k: int = DEFAULT_K) -> dict:
    """关键词空格分隔；返回 top-k {case_id, title, hits}。"""
    kws = [w for w in keywords.split() if w]
    if not kws:
        raise ValueError("keywords 为空")
    scored = []
    for c in _load_cases():
        text = c["title"] + " " + c["facts"]
        hits = sum(1 for w in kws if w in text)
        if hits > 0:
            scored.append((hits, c["case_id"], c["title"]))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return {
        "keywords": kws,
        "results": [{"case_id": cid, "title": title, "hits": hits}
                    for hits, cid, title in scored[:k]],
        "total": len(scored),
    }

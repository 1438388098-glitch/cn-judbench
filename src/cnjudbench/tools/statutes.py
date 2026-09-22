"""法条检索与条文获取（impl-P2 §2 前两行）。

- ``search_statute``：lawkb 法名/别名子串匹配（确定性，无排序魔法，库序即序）；
- ``get_article``：走 ``lawkb.resolve.resolve_article``——与机检 CiteGuard 同一
  解析路径，保证金样与库不打架（impl-P2 §10）。
"""

from __future__ import annotations

from datetime import date

from ..lawkb.resolve import normalize_law_name, resolve_article
from ..lawkb.store import LawkbStore

MAX_HITS = 5


def search_statute(*, store: LawkbStore, query: str, as_of: str) -> dict:
    """法名子串检索；as_of 过滤「该日存在生效版本」的法。"""
    q = normalize_law_name(query)
    if len(q) < 2:
        raise ValueError("query 过短（≥2 字）")
    as_of_d = date.fromisoformat(as_of)

    hits = []
    for law_id, meta in store.laws.items():
        names = [normalize_law_name(n) for n in meta.names]
        matched = next((orig for orig, n in zip(meta.names, names) if q in n or n in q), None)
        if matched is None:
            continue
        active = any(
            v.effective_from <= as_of_d and (v.effective_to is None or as_of_d < v.effective_to)
            for v in store.versions.values() if v.law_id == law_id
        )
        hits.append({
            "law_id": law_id,
            "law": meta.names[0],
            "matched_as": matched,
            "active_at_as_of": active,
        })
    return {"query": query, "as_of": as_of, "hits": hits[:MAX_HITS], "total": len(hits)}


def get_article(*, store: LawkbStore, law: str, article: str, as_of: str) -> dict:
    """按 as_of 取条文；unknown_in_lawkb 等状态如实返回（unknown 分列不记幻觉）。"""
    r = resolve_article(law, article, date.fromisoformat(as_of), store)
    return {
        "law": law,
        "article": article,
        "as_of": as_of,
        "status": r.status,
        "version_id": r.version_id,
        "text": r.text,
    }

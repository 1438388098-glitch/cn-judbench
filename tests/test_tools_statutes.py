# -*- coding: utf-8 -*-
"""tools/statutes 直接单测（round-6，c432）：法条检索/取条文是判分高危面，
此前零直接覆盖——search 的子串/as_of 语义与 get_article 的四态透传在此锁定。
"""

from datetime import date

import pytest

from cnjudbench.tools.statutes import get_article, search_statute


def test_search_statute_substring_hits(store):
    out = search_statute(store=store, query="民法", as_of="2024-06-01")
    ids = [h["law_id"] for h in out["hits"]]
    assert "npc_civil_code" in ids and "npc_general_principles" in ids
    assert out["total"] == len(out["hits"]) or len(out["hits"]) == 5  # MAX_HITS 截断语义
    assert len(out["hits"]) <= 5
    # hit 结构：法名原样 + 归一匹配名 + as_of 活性
    first = next(h for h in out["hits"] if h["law_id"] == "npc_civil_code")
    assert first["active_at_as_of"] is True
    assert first["matched_as"]


def test_search_statute_active_flag_respects_as_of(store):
    # 民法典 2021-01-01 施行：之前不活跃，之后活跃
    before = search_statute(store=store, query="民法典", as_of="2020-12-31")
    after = search_statute(store=store, query="民法典", as_of="2021-06-01")
    hit_before = next(h for h in before["hits"] if h["law_id"] == "npc_civil_code")
    hit_after = next(h for h in after["hits"] if h["law_id"] == "npc_civil_code")
    assert hit_before["active_at_as_of"] is False
    assert hit_after["active_at_as_of"] is True


def test_search_statute_query_too_short(store):
    with pytest.raises(ValueError):
        search_statute(store=store, query="法", as_of="2024-06-01")


def test_get_article_ok_path(store):
    out = get_article(store=store, law="中华人民共和国民法典", article="188", as_of="2021-06-01")
    assert out["status"] == "ok"
    assert out["version_id"]
    assert "向人民法院请求保护民事权利" in out["text"]  # 三年诉讼时效条文正文在场


def test_get_article_unresolved_law_passthrough(store):
    # 法名本身不可解析 → unresolved_law；可解析但库无此条 → unknown_in_lawkb（两态分列）
    out = get_article(store=store, law="不存在的法规", article="1", as_of="2024-06-01")
    assert out["status"] == "unresolved_law"
    assert out["text"] is None


def test_get_article_known_law_missing_article(store):
    # 可解析的法 + 库外条号 → unknown_in_lawkb（惰性锚白名单的语义来源）；
    # 2023 版民诉条入库后，用仍在队列的 246 条锁这个语义
    out = get_article(store=store, law="民事诉讼法", article="246", as_of="2024-06-01")
    assert out["status"] == "unknown_in_lawkb"
    assert out["text"] is None


def test_get_article_civil_procedure_2023_articles(store):
    # round-9 入库回归：民诉 2023 版四条真实解析（原 37 题惰性锚簇）
    for no, vid in (("122", "msf_122_2023"), ("126", "msf_126_2023"),
                    ("128", "msf_128_2023"), ("171", "msf_171_2023")):
        out = get_article(store=store, law="民事诉讼法", article=no, as_of="2024-06-01")
        assert out["status"] == "ok", (no, out["status"])
        assert out["version_id"] == vid
    # 时点边界：2023 版施行前一日不可用（2024-01-01 起施行）
    early = get_article(store=store, law="民事诉讼法", article="122", as_of="2023-12-31")
    assert early["status"] == "not_yet_effective"


def test_get_article_not_yet_effective(store):
    # 费办 2007-04-01 施行：前一日不可用（round-4 入库条目的时点边界）
    out = get_article(store=store, law="诉讼费用交纳办法", article="13", as_of="2007-03-31")
    assert out["status"] == "not_yet_effective"


def test_get_article_version_id_contract(store):
    # 与机检 CiteGuard 同一解析路径的契约：get_article 透传库内 version_id
    out = get_article(store=store, law="诉讼费用交纳办法", article="13", as_of="2024-06-01")
    assert out["status"] == "ok"
    assert out["version_id"] == "fee_13_2007"

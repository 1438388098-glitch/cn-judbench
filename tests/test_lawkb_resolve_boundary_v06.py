# -*- coding: utf-8 -*-
"""R13 lawkb 解析边界（c222/c223）：

- c222 时效边界：``effective_from <= as_of < effective_to`` 左闭右开——
  生效当天即在窗；换版当天旧版必须出窗（同一 as_of 恰一版本）；
- c223 normalize_article_no 变体归一（第/条剥离、中文数字、之一后缀、全角）。
"""

from datetime import date
from pathlib import Path

import pytest

from cnjudbench.lawkb.resolve import normalize_article_no, resolve_article
from cnjudbench.lawkb.store import LawkbStore

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def store():
    return LawkbStore.load(REPO / "lawkb")


def test_c222_effective_on_first_day(store):
    # 刑法264 首版 1997-10-01 施行：生效当天即在窗
    r = resolve_article("中华人民共和国刑法", "264", date(1997, 10, 1), store)
    assert r.status == "ok" and r.version_id == "cl_264_1997"


def test_c222_version_flip_on_replacement_day(store):
    # 第二版 2011-05-01 生效：当天旧版出窗、新版入窗（左闭右开，恰一在窗）
    r = resolve_article("中华人民共和国刑法", "264", date(2011, 5, 1), store)
    assert r.status == "ok" and r.version_id == "cl_264_2011"
    r_prev = resolve_article("中华人民共和国刑法", "264", date(2011, 4, 30), store)
    assert r_prev.status == "ok" and r_prev.version_id == "cl_264_1997"


def test_c222_not_yet_effective_before_first_version(store):
    r = resolve_article("中华人民共和国刑法", "264", date(1990, 1, 1), store)
    assert r.status == "not_yet_effective"  # 全部版本 effective_from > as_of


@pytest.mark.parametrize("raw,expect", [
    ("第264条", "264"),
    ("第二百六十四条", "264"),
    ("第253之一条", "253之一"),
    ("253 之一", "253之一"),
    ("２６４", "264"),          # 全角
    ("第 二 百 六 十 四 条", "264"),
    ("第二百五十三条之一", "253之一"),
])
def test_c223_normalize_article_no_variants(raw, expect):
    assert normalize_article_no(raw) == expect, raw


def _synth_store(versions):
    """c403 合成库：手工构造缝隙/双因场景（真实库无缝隙）。"""
    import hashlib

    from cnjudbench.lawkb.schema import ArticleVersion, LawMeta
    from cnjudbench.lawkb.store import LawkbStore

    law = LawMeta(law_id="synth_law", names=["合成法"], level="law",
                  promulgated_on=date(2000, 1, 1))
    vs, by_key, texts = {}, {}, {}
    for v in versions:
        h = "sha256:" + hashlib.sha256(v["version_id"].encode()).hexdigest()
        av = ArticleVersion(
            law_id="synth_law", article_no=v["article_no"],
            version_id=v["version_id"], text_hash=h,
            effective_from=date.fromisoformat(v["from"]),
            effective_to=date.fromisoformat(v["to"]) if v.get("to") else None,
            text_ref="synth")
        vs[v["version_id"]] = av
        by_key.setdefault(("synth_law", v["article_no"]), []).append(av)
        texts[v["version_id"]] = "text"
    return LawkbStore(root=REPO, store_version="lawkb-2026.09.24",
                      laws={"synth_law": law}, versions=vs, by_key=by_key,
                      alias={"合成法": "synth_law"}, texts=texts)


def test_c403_ladder_priority_gap_and_double_cause():
    """c403：状态阶梯优先级金样（隐式约定显式化）。

    零在窗时先查未来版本（not_yet_effective）再查已失效（wrong_vintage）；
    check/谓词侧三档时效同映射 stale，次序无判分影响，但 cit_validity 按模型
    自答 status 分档，故次序必须锁定。"""
    s = _synth_store([
        {"version_id": "sv_264_2010", "article_no": "264", "from": "2010-01-01", "to": "2012-01-01"},
        {"version_id": "sv_264_2030", "article_no": "264", "from": "2030-01-01"},
    ])
    r = resolve_article("合成法", "264", date(2020, 6, 1), s)
    assert r.status == "not_yet_effective"  # 未来版本优先（wrong_vintage 被遮蔽）

    s2 = _synth_store([
        {"version_id": "sv_264_2010", "article_no": "264", "from": "2010-01-01", "to": "2015-01-01"},
        {"version_id": "sv_264_2021", "article_no": "264", "from": "2021-01-01"},
    ])
    r2 = resolve_article("合成法", "264", date(2018, 6, 1), s2)
    assert r2.status == "not_yet_effective"  # 缝隙场景非 not_effective_on_as_of

    s3 = _synth_store([
        {"version_id": "sv_264_2010", "article_no": "264", "from": "2010-01-01", "to": "2015-01-01"},
    ])
    r3 = resolve_article("合成法", "264", date(2020, 6, 1), s3)
    assert r3.status == "wrong_vintage"  # 无未来版本时才轮到已失效

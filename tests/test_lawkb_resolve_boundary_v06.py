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

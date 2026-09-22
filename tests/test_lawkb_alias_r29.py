# -*- coding: utf-8 -*-
"""R29：法名别名括注后缀归一——修 ah-104 实测暴露的 statute 必引假阴性。

考生引用常带「（2020年第二次修正）」等括注，原实现 alias 精确命中失败
→ 必引覆盖 0/1、unresolved_law。本批在加载期注册剥尾括注变体；
冲突仍报错。用 ah-104 真实考生答案的原句回归。
"""

from __future__ import annotations

from pathlib import Path

from cnjudbench.lawkb.resolve import strip_bracket_note
from cnjudbench.lawkb.store import LawkbStore

REPO = Path(__file__).resolve().parents[1]


def _store() -> LawkbStore:
    return LawkbStore.load(REPO / "lawkb")


def test_strip_bracket_note_variants():
    assert strip_bracket_note("最高人民法院关于审理民间借贷案件适用法律若干问题的规定（2020年第二次修正）") \
        == "最高人民法院关于审理民间借贷案件适用法律若干问题的规定"
    assert strip_bracket_note("某法(试行)（2021年修正）") == "某法"
    # 全括注名剥空则原文返回
    assert strip_bracket_note("（试行）") == "（试行）"
    # 无括注原样
    assert strip_bracket_note("中华人民共和国民法典") == "中华人民共和国民法典"


def test_alias_resolves_decorated_citation():
    """ah-104 考生原句：法名+修正括注经 alias_lookup 必须命中同一 law_id。"""
    from cnjudbench.lawkb.resolve import alias_lookup

    store = _store()
    plain = "最高人民法院关于审理民间借贷案件适用法律若干问题的规定"
    decorated = plain + "（2020年第二次修正）"
    assert store.alias.get(decorated) is None  # 注册侧只登记规范名
    assert alias_lookup(store, decorated) == alias_lookup(store, plain) \
        == "spc_private_lending_2015"
    assert alias_lookup(store, plain + "(2020年第二次修正)") == "spc_private_lending_2015"


def test_alias_exact_names_unchanged():
    """回归：全部原始法名映射不受变体注册影响。"""
    store = _store()
    assert store.alias["中华人民共和国民法典"] == "npc_civil_code"
    assert store.alias["中华人民共和国刑法"] == "npc_criminal_law"
    assert store.alias["民间借贷规定"] == "spc_private_lending_2015"
    assert len(store.laws) == 12

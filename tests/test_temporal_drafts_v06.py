# -*- coding: utf-8 -*-
"""R28 时间效力轴 READY 草稿机检（规格 at-201/202/203/210 → 判定面草稿 ct-201..211）。

与 tests/test_drafts_v06.py（a_irac ah 系）同纪律：
- 草稿瘦字段与正式 Item schema 同标，draft/split 隔离；
- 每题判定窗在 lawkb 中按题面 as_of 解析出 gold.expect_status；
- canary 不与正式集撞值；spec 外增补题（ct-211，at-210 对偶窗）须在 draft_notes 声明。
- 草稿 id 用 ct- 前缀：与 ah 系（a_irac IRAC 叙事草稿）、at 系（附录 B 规格 id）三方区分。
差异：cit 族 gold 为 list[dict]（status_ladder 取 gold[0] 判分窗），
题面与金样都是单引用单窗（与正式 cit 形态一致）。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# (id, 判定窗 as_of, expect_status)——expect 由附录 B-2 规格窗预注册
SPECS = {
    "ct-201": ("2021-06-01", "wrong_vintage"),
    "ct-202": ("2021-06-01", "wrong_vintage"),
    "ct-203": ("2014-06-01", "not_yet_effective"),
    "ct-210": ("2019-06-01", "not_yet_effective"),
    "ct-211": ("2021-06-01", "ok"),  # 规格外对照（at-210 对偶窗），notes 已声明
}


def _drafts():
    out = {}
    for did in SPECS:
        p = REPO / "data" / "drafts" / "cit_validity" / f"{did}.json"
        out[did] = json.loads(p.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="module")
def store():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.lawkb.store import LawkbStore

    return LawkbStore.load(REPO / "lawkb")


@pytest.mark.parametrize("did", sorted(SPECS))
def test_c356_at_draft_判定窗解析等于金样(store, did):
    from cnjudbench.lawkb.resolve import resolve_article

    d = _drafts()[did]
    want_as_of, want_status = SPECS[did]
    assert d["as_of"] == want_as_of, f"{did} 题面基准日与规格窗不符"
    g = d["gold"]
    assert isinstance(g, list) and len(g) == 1, "cit 族判分面=单窗（status_ladder gold[0]）"
    g0 = g[0]
    assert g0["as_of"] == want_as_of and g0["expect_status"] == want_status
    r = resolve_article(d["law_anchors"][0]["law"], str(d["law_anchors"][0]["article"]),
                        date.fromisoformat(want_as_of), store)
    assert r.status == want_status, f"{did}: 库解析 {r.status} ≠ 金样 {want_status}"


@pytest.mark.parametrize("did", sorted(SPECS))
def test_c357_at_draft_契约与隔离(did):
    d = _drafts()[did]
    for key in ("id", "task_id", "capability", "difficulty", "interaction",
                "roles", "domain", "output_type", "instruction", "input",
                "gold", "law_anchors", "as_of", "canary", "split",
                "predicates_ref", "draft", "draft_status", "draft_notes"):
        assert key in d, f"{did} 缺字段 {key}"
    assert d["draft"] is True and d["draft_status"] == "awaiting_examinee"
    assert d["split"] == "draft"
    assert d["task_id"] == "cit_validity" and d["capability"] == "Cit"
    # 题面引用串须含法名（防 input 与 gold 脱节；条号中文数字由
    # normalize_article_no 归一，正式题 input 亦用中文条号）。
    # 法名内嵌书名号（时间效力规定），input 内层用〈〉——比较时全剥。
    strip = lambda s: re.sub(r"[《》〈〉]", "", s)
    assert strip(d["gold"][0]["law"]) in strip(d["input"]), f"{did} input 未含 gold 法名"
    # 规格外增补题必须声明
    if did not in ("ct-201", "ct-202", "ct-203", "ct-210"):
        assert "规格外" in d["draft_notes"]


def test_c358_at_draft_canary_不撞正式集():
    drafts = _drafts()
    official = set()
    for p in (REPO / "data" / "public").glob("*.jsonl"):
        official |= set(re.findall(r'"canary":\s*"([^"]+)"',
                                   p.read_text(encoding="utf-8")))
    for did, d in drafts.items():
        assert d["canary"] not in official, f"{did} canary 与正式集撞值"


def test_c359_at_draft_同条成对题覆盖三判定状态():
    """ct-210/ct-211 同条跨施行日成对；全组覆盖 ok/wrong_vintage/not_yet。"""
    d = _drafts()
    assert d["ct-210"]["law_anchors"][0]["law"] == d["ct-211"]["law_anchors"][0]["law"]
    assert d["ct-210"]["gold"][0]["expect_status"] != d["ct-211"]["gold"][0]["expect_status"]
    statuses = {d[k]["gold"][0]["expect_status"] for k in d}
    assert statuses == {"ok", "wrong_vintage", "not_yet_effective"}

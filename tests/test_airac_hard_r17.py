"""R17：a_irac hard 子集（ah-001..006）——金样自洽、判分口径与放水负例。

自洽以 mock:gold 全管线验证（gold 作答必须满分，包括 statute 锚经 lawkb
三检、refuse/over_promise 安全轨、any-of 多解口径）；
负例验证错误条号/漏引锚不得满分。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cnjudbench import cli
from cnjudbench.schemas.item import Item

REPO = Path(__file__).resolve().parents[1]


def _items() -> list[dict]:
    path = REPO / "data" / "public" / "a_irac_reason.jsonl"
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if d["id"].startswith("ah-"):
                out.append(d)
    return out


def test_hard_items_present_and_valid():
    items = _items()
    assert len(items) == 10  # ah-001..006 复合争点 + ah-101..104 要素不点名（R25）
    canaries = [it["canary"] for it in items]
    assert len(set(canaries)) == len(canaries)
    assert {it["difficulty"] for it in items} == {4}
    for it in items:
        Item.model_validate(it)  # schema + 适用面
        # R16 多解口径：acceptable 条号不得与主条号相同
        for acc in it["gold"].get("acceptable_articles", []):
            assert acc["article"] != it["gold"]["rule_article"], it["id"]


def test_hard_anchors_in_lawkb():
    """ah-005 的时间效力规定等锚必须可经别名解析且条文在库。"""
    from cnjudbench.lawkb.store import LawkbStore

    store = LawkbStore.load(REPO / "lawkb")
    for it in _items():
        for anchor in it["law_anchors"]:
            law_id = store.alias.get(anchor["law"])
            assert law_id is not None, (it["id"], anchor["law"])
            assert (law_id, anchor["article"]) in store.by_key, (it["id"], anchor)


def test_run_all_airac_mock_gold_end_to_end(tmp_path, monkeypatch):
    """mock:gold → 32 题（19 基础 + 10 hard + 3 应拒 R37）全对，证明金样自洽。"""
    monkeypatch.chdir(REPO)
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "a_irac_reason", "--model", "mock:gold",
                   "--out", str(out)])
    assert rc == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    pt = s["per_task"]["a_irac_reason"]
    assert pt["machine_mean_str"] == "100.00"
    n_items = len(s["tasks"]["a_irac_reason"]["items"])
    assert n_items == 32
    for it in s["tasks"]["a_irac_reason"]["items"]:
        assert float(it["score"]) == 100.0, it["id"]


@pytest.mark.parametrize("hid,article", [
    ("ah-002", "188"),   # 保证期间题答成诉讼时效
    ("ah-004", "509"),   # 违约金/定金题答成全面履行
    ("ah-005", "577"),   # 溯及力题只引民法典实体条
])
def test_wrong_article_not_full_marks(hid, article):
    """引错主条号且不在 acceptable 集合 → rule_article any-of 必须判 0。"""
    from cnjudbench.predicates.ftp import field
    from cnjudbench.predicates.base import EvalContext

    raw = next(it for it in _items() if it["id"] == hid)
    item = Item.model_validate(raw)

    class Store:
        alias = {}

    class Task:
        output_type = "structured"

    class P:
        on_fail = "partial"
        model_extra = {"path": "rule_article", "match": "article_set"}

    ctx = EvalContext(
        task=Task(), item=item, answer={"rule_article": article},
        answer_text=article, claims=[], claim_status="ok", store=Store(), checks=[],
    )
    r = field(ctx, P(), 0)
    assert r.passed is False and r.pass_ratio == 0.0

"""R17：a_irac hard 子集——金样自洽、判分口径与放水负例。

v0.5 Phase 1 剖减后 ah- 仅存 ah-005（其余 ah-001..004/006/101..104 为
T4a 全分饱和题，移入 data/archive/a_irac_reason.jsonl，见
docs/difficulty-audit-v05.md）；v0.5 Phase 3a 新增时间效力轴 at-001..018
（as_of 新旧法衔接/程序时效交叉/民间借贷版本，见
scripts/add_airac_temporal_v05.py）。本文件保留 ah-005 的锚解析检查、
mock:gold 全管线自洽与 any-of 负例口径，并覆盖 at- 家族的锚在库与
旧条号负例。

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


def _items(prefixes: tuple[str, ...] = ("ah-",)) -> list[dict]:
    path = REPO / "data" / "public" / "a_irac_reason.jsonl"
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if d["id"].startswith(prefixes):
                out.append(d)
    return out


def test_hard_items_present_and_valid():
    items = _items()
    assert len(items) == 1  # v0.5 Phase 1 剖减后仅存 ah-005（其余入 archive）
    canaries = [it["canary"] for it in items]
    assert len(set(canaries)) == len(canaries)
    assert {it["difficulty"] for it in items} == {4}
    for it in items:
        Item.model_validate(it)  # schema + 适用面
        # R16 多解口径：acceptable 条号不得与主条号相同
        for acc in it["gold"].get("acceptable_articles", []):
            assert acc["article"] != it["gold"]["rule_article"], it["id"]


def test_hard_anchors_in_lawkb():
    """ah-005 与 at-001..018 的时间效力/民法典/民诉法/借贷规定等锚必须可解析且条文在库。"""
    from cnjudbench.lawkb.store import LawkbStore

    store = LawkbStore.load(REPO / "lawkb")
    for it in _items(("ah-", "at-")):
        for anchor in it["law_anchors"]:
            law_id = store.alias.get(anchor["law"])
            assert law_id is not None, (it["id"], anchor["law"])
            assert (law_id, anchor["article"]) in store.by_key, (it["id"], anchor)


def test_temporal_family_shape():
    """at- 家族：18 题、锚规范全部现行有效（as_of ≥ 生效日）、难度 4、canary 唯一。"""
    items = _items(("at-",))
    assert len(items) == 18
    canaries = [it["canary"] for it in items]
    assert len(set(canaries)) == len(canaries)
    assert {it["difficulty"] for it in items} == {4}
    for it in items:
        Item.model_validate(it)
        for anchor in it["law_anchors"]:
            if anchor.get("effective_on"):
                assert it["as_of"] >= anchor["effective_on"], (it["id"], anchor)


def test_run_all_airac_mock_gold_end_to_end(tmp_path, monkeypatch):
    """mock:gold → 30 题（12 存量 + 18 时间效力轴 at-）全对，证明金样自洽。

    12 存量 = 4 hard + 3 应拒（R37）+ 5 地板/网格保底；18 新增 =
    新旧法衔接 8 + 程序时效交叉 5 + 民间借贷版本 5（v0.5 Phase 3a）。
    """
    monkeypatch.chdir(REPO)
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "a_irac_reason", "--model", "mock:gold",
                   "--out", str(out)])
    assert rc == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    pt = s["per_task"]["a_irac_reason"]
    assert pt["machine_mean_str"] == "100.00"
    n_items = len(s["tasks"]["a_irac_reason"]["items"])
    assert n_items == 30
    for it in s["tasks"]["a_irac_reason"]["items"]:
        assert float(it["score"]) == 100.0, it["id"]


@pytest.mark.parametrize("hid,article", [
    ("ah-005", "577"),   # 溯及力题只引民法典实体条（其余 ah- 入 archive）
    ("at-012", "227"),   # 执行异议题引民诉法 2021 修正前旧条号
    ("at-014", "24"),    # 2018 未约定利息题答成 24——2015 版中该规则就在第25条，24 系臆测条号
])
def test_wrong_article_not_full_marks(hid, article):
    """引错主条号且不在 acceptable 集合 → rule_article any-of 必须判 0。"""
    from cnjudbench.predicates.ftp import field
    from cnjudbench.predicates.base import EvalContext

    raw = next(it for it in _items(("ah-", "at-")) if it["id"] == hid)
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

"""P0b e2e 冒烟（impl-P0b §9 DoD 2/3/4/6）：

- 3 任务包 Mock run-all → manifest + summary 可产出；
- 分数恒为 0.00–100.00 两位小数；
- wrong_vintage / 幻觉引用负例 → 0.00 或 cap 且 taxonomy 正确；
- field_keep 篡改 → cap_50；
- Mock 复跑翻转率 0（确定性）。
"""

import json
import re
from pathlib import Path

from cnjudbench.adapters.mock import MockAdapter, mock_gold_adapter
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.runner.account import Accountant
from cnjudbench.runner.evaluate import evaluate_item, load_task_package, run_task
from cnjudbench.schemas.item import Item
from cnjudbench.validate.items import validate_items_dir
from cnjudbench.validate.tasks import validate_task_dir

REPO = Path(__file__).resolve().parents[1]
TASK_IDS = ("cit_validity", "u_element_extract", "s_charge_subsume")
TWO_DECIMALS = re.compile(r"^\d+\.\d{2}$")


def _items(tid):
    path = REPO / "data" / "public" / f"{tid}.jsonl"
    return [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _pkg(tid):
    return load_task_package(REPO / "tasks" / tid)


def test_three_packages_validate_clean(store):
    for tid in TASK_IDS:
        assert validate_task_dir(REPO / "tasks" / tid) == [], tid
        assert validate_items_dir(REPO / "data" / "public" / f"{tid}.jsonl",
                                  REPO / "tasks") == [], tid


def test_mock_gold_run_all_full_score():
    """DoD 2：3 任务包 mock:gold 跑通，全题满分两位小数。"""
    store = LawkbStore.load(REPO / "lawkb")
    for tid in TASK_IDS:
        run = run_task(REPO / "tasks" / tid,
                       REPO / "data" / "public" / f"{tid}.jsonl",
                       lambda item: mock_gold_adapter(item, store), store)
        assert run.results, tid
        for r in run.results:
            assert r.score is not None, f"{tid}/{r.item_id}: {r.error}"
            assert r.display == "100.00", f"{tid}/{r.item_id} = {r.display}"
            assert TWO_DECIMALS.match(r.display)
        assert run.mean == 100.0


def test_scores_always_two_decimals_in_range():
    """即便出错路径，display 也只能是 xx.xx 或 n/a（null ≠ 0.00）。"""
    store = LawkbStore.load(REPO / "lawkb")
    from cnjudbench.scale import fmt2

    for v in (0.0, 33.335, 87.654, 100.0):
        assert TWO_DECIMALS.match(fmt2(v))


def test_dod3_wrong_vintage_sample_zero_with_taxonomy():
    """DoD 3a：条号引对但 as_of 早于施行（wrong_vintage 型）→ 0.00 + stale_statute。"""
    store = LawkbStore.load(REPO / "lawkb")
    task, preds = _pkg("s_charge_subsume")
    items = {Item.model_validate_json(l).id: Item.model_validate_json(l)
             for l in _items("s_charge_subsume")}
    item = items["s-006"]  # 291之二（2021-03-01 施行），as_of 2021-09-01
    gold = json.loads(next(l for l in _items("s_charge_subsume") if '"s-006"' in l))["gold"]
    stale = dict(gold,
                 citations=[{"law": "中华人民共和国刑法", "article": "291之二",
                             "as_of": "2020-06-01"}],
                 defendant_name="孙某")
    r = evaluate_item(task, preds, item,
                      MockAdapter(lambda _p: json.dumps(stale, ensure_ascii=False)), store)
    assert r.display == "0.00"
    assert "stale_statute" in r.taxonomy


def test_dod3_fabricated_version_id_zero():
    """DoD 3b：幻觉 version_id（其余全对）→ 0.00 + fabricated_case。"""
    store = LawkbStore.load(REPO / "lawkb")
    task, preds = _pkg("cit_validity")
    lines = _items("cit_validity")
    item = next(Item.model_validate_json(l) for l in lines
                if Item.model_validate_json(l).id == "cit-002")
    g = item.gold[0]
    bad = {"law": g["law"], "article": g["article"], "as_of": str(item.as_of),
           "status": g["expect_status"], "version_id": " hallucinated_v1",
           "citations": [{"law": g["law"], "article": g["article"], "as_of": str(item.as_of)}]}
    r = evaluate_item(task, preds, item,
                      MockAdapter(lambda _p: json.dumps(bad, ensure_ascii=False)), store)
    assert r.display == "0.00"
    assert "fabricated_case" in r.taxonomy


def test_dod4_field_keep_tamper_caps_at_50():
    """DoD 4：field_keep 篡改（case_no 改写）→ cap_50 = 50.00。"""
    store = LawkbStore.load(REPO / "lawkb")
    task, preds = _pkg("u_element_extract")
    lines = _items("u_element_extract")
    item = next(Item.model_validate_json(l) for l in lines
                if Item.model_validate_json(l).id == "u-001")
    gold = item.gold
    tampered = {"amount": gold["amount"], "date": gold["date"],
                "case_no": "（2030）京01民终9999号"}
    r = evaluate_item(task, preds, item,
                      MockAdapter(lambda _p: json.dumps(tampered, ensure_ascii=False)), store)
    assert r.display == "50.00"
    assert "state_drift" in r.taxonomy


def test_dod6_mock_rerun_flip_rate_zero():
    """DoD 6：Mock 复跑逐题（display, taxonomy, score）全等 → 翻转率 0。"""
    store = LawkbStore.load(REPO / "lawkb")

    def snapshot():
        out = []
        for tid in TASK_IDS:
            run = run_task(REPO / "tasks" / tid,
                           REPO / "data" / "public" / f"{tid}.jsonl",
                           lambda item: mock_gold_adapter(item, store), store)
            out += [(r.item_id, r.display, tuple(r.taxonomy), r.score) for r in run.results]
        return out

    assert snapshot() == snapshot()


def test_accounting_judge_calls_stay_zero():
    """P0b 全链路 judge_calls 恒 0；token 账本随调用累加。"""
    store = LawkbStore.load(REPO / "lawkb")
    task, preds = _pkg("cit_validity")
    items = [Item.model_validate_json(l) for l in _items("cit_validity")]
    acc = Accountant()
    for item in items:
        evaluate_item(task, preds, item, mock_gold_adapter(item, store), store,
                      accountant=acc)
    assert acc.judge_calls == 0
    assert acc.prompt_tokens > 0 and acc.completion_tokens > 0
    assert acc.est_cost_usd is None  # P0b 无价格表

"""baselines 两列（DESIGN v0.4 §6.3）：random/rules 同管线口径。

- 规则基线禁读 gold：只允许题面正则 + 法定公式（受理费分段累进）；
- 随机基线按 item_id 确定性播种，同题两次答案逐字一致；
- summary.baselines 落盘 random/rules 的 grand_eq 与 per_task。
"""

from __future__ import annotations

import json
from pathlib import Path

from cnjudbench import cli
from cnjudbench.baselines import _fee_rule, random_answer, rules_answer
from cnjudbench.baselines import (
    SUPPORTED_TASKS,
    baseline_adapter_factory,
)
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.runner.evaluate import run_task
from cnjudbench.validate.items import load_items_file

REPO = Path(__file__).resolve().parents[1]


def _mk_item(task_id: str, output_type: str, input_text: str, gold, **kw) -> "Item":
    from cnjudbench.schemas.item import Item
    return Item.model_validate({
        "id": kw.get("id", "x-001"), "task_id": task_id, "capability": "U",
        "difficulty": 2, "interaction": "L1", "roles": ["lawyer"],
        "domain": kw.get("domain", "civil_commercial"), "output_type": output_type,
        "hcut": ["Cit"], "instruction": "作答", "input": input_text, "gold": gold,
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "577"}],
        "as_of": kw.get("as_of", "2024-06-01"), "canary": "CNJB-CANARY-0001",
        "split": "public", "contamination_risk": "low", "source": "synthetic",
    })


def test_fee_rule_matches_statute_and_gold():
    """分段累进须与金样一致：250000→5050（g-01），8000→50（≤1万每件50）。"""
    assert _fee_rule(250000) == 5050
    assert _fee_rule(8000) == 50
    assert _fee_rule(10000) == 50
    assert _fee_rule(0) == 0


def test_rules_never_read_gold():
    """规则/随机答案只依赖题面与锚点：同一题面不同 gold 产出不变。"""
    a = _mk_item("u_element_extract", "extract", "借款100000元，约定2022-05-01还款，案号（2023）京0105民初1234号。",
                 gold={"amount": 1, "date": "1900-01-01", "case_no": "x"})
    b = _mk_item("u_element_extract", "extract", "借款100000元，约定2022-05-01还款，案号（2023）京0105民初1234号。",
                 gold={"amount": 999, "date": "2999-09-09", "case_no": "y"})
    assert rules_answer(a) == rules_answer(b)
    assert random_answer(a) == random_answer(b)


def test_random_deterministic_by_item_id():
    a = _mk_item("cit_validity", "structured", "题干", gold=[{"expect_status": "ok"}], id="cit-001")
    b = _mk_item("cit_validity", "structured", "题干", gold=[{"expect_status": "ok"}], id="cit-001")
    assert random_answer(a) == random_answer(b)


def test_rules_u_element_extracts_last_mentioned():
    it = _mk_item("u_element_extract", "extract",
                  "借款合同纠纷，案号（2023）京0105民初1234号。2021年5月1日出借100000元，2022年5月1日到期。",
                  gold={"amount": 100000, "date": "2022-05-01", "case_no": "（2023）京0105民初1234号"})
    ans = json.loads(rules_answer(it))
    assert ans["amount"] == 100000
    assert ans["date"] == "2022-05-01"
    assert "1234号" in ans["case_no"]


def test_baseline_adapters_through_pipeline(store: LawkbStore):
    """random/rules 经 run_task 全管线判分；随机基线显著低于满分。"""
    task_dir = REPO / "tasks" / "s_charge_subsume"
    items_path = REPO / "data" / "public" / "s_charge_subsume.jsonl"
    for kind in ("random", "rules"):
        run = run_task(task_dir, items_path, baseline_adapter_factory(kind), store)
        assert all(r.score is not None for r in run.capability_results), kind
        assert run.mean < 100.0, kind


def test_baselines_in_summary(tmp_path, monkeypatch):
    """run-all 全链路：summary.baselines 含 random/rules 两列（§6.3）。"""
    monkeypatch.chdir(REPO)
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "s_charge_subsume,u_element_extract",
                   "--model", "mock:gold", "--out", str(out)])
    assert rc == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert set(s["baselines"]) == {"random", "rules"}
    for kind in ("random", "rules"):
        b = s["baselines"][kind]
        assert b["grand_eq"] != "n/a"
        assert set(b["per_task"]) >= {"s_charge_subsume", "u_element_extract"}
    # 随机基线必须显著低于规则基线与真实模型（否则机检无信息）
    assert float(s["baselines"]["random"]["grand_eq"]) < float(s["baselines"]["rules"]["grand_eq"])
    assert float(s["baselines"]["random"]["grand_eq"]) < float(s["capability"]["grand_eq"])


def test_supported_tasks_constant():
    assert "tool_search_statute" not in SUPPORTED_TASKS
    assert "gaia_fee_deadline" in SUPPORTED_TASKS


def test_baselines_never_cite_scoring_anchors():
    """R17 泄题回归：a_irac 基线不得引用 law_anchors（判分锚，题面不可见）。

    修复前 random/rules 直接抄锚 → a_irac 双基线 96 分、高于真实考生。
    cit_validity 例外：其锚即题面给出的待判引用（考试可见输入）。
    """
    from cnjudbench.baselines import random_answer, rules_answer
    from cnjudbench.schemas.item import Item

    path = REPO / "data" / "public" / "a_irac_reason.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = Item.model_validate_json(line)
        anchor = item.law_anchors[0]
        for fn in (random_answer, rules_answer):
            ans = json.loads(fn(item))
            for c in ans.get("citations") or []:
                hit = c.get("article") == anchor.article and c.get("law") == anchor.law
                assert not hit, (item.id, fn.__name__, c)

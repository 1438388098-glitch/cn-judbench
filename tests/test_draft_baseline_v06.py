# -*- coding: utf-8 -*-
"""R32 ct 草稿基线预演金样（c363-c364）。

真考生轮前的区分度锚点：把 ct 草稿漂洗成合法 Item 后分别跑
mock:gold / rules 基线（同判分管线、确定性输出）——

- mock:gold 必须 5×100 自证（金样质量，与 c362 互为印证）；
- rules 基线在 4 个陷阱窗（wrong_vintage/not_yet）全 0、仅在 ct-211
  对照窗（ok 判定）得满分——「判别非 ok 状态」正是本轴考点，
  rules 得 20.00 均分为设计预期，同时也是草稿阶段的泄题前兆门禁
  （正式集对应物 = c161）：若未来 rules 均分抬升，说明题面/金样
  把答案泄给了规则型作答。

random 基线非确定性（random_answer 无种子），不入机检只入台账记录
（首演 48.00，ct-201 撞对 wrong_vintage 得 100 属单题偶然）。
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DRAFT_IDS = ("ct-201", "ct-202", "ct-203", "ct-210", "ct-211")


def _bleached_rows() -> list[dict]:
    rows = []
    for did in DRAFT_IDS:
        d = json.loads((REPO / "data" / "drafts" / "cit_validity" / f"{did}.json")
                       .read_text(encoding="utf-8"))
        for k in ("draft", "draft_status", "draft_notes"):
            d.pop(k, None)
        d["canary"] = f"CNJB-CANARY-{hashlib.md5(d['id'].encode()).hexdigest()[:4]}"
        d["split"] = "public"
        rows.append(d)
    return rows


def _run_kind(kind: str, store, rows: list[dict]):
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.adapters.mock import mock_gold_adapter
    from cnjudbench.baselines import baseline_adapter_factory
    from cnjudbench.runner.evaluate import run_task

    fac = ((lambda it: mock_gold_adapter(it, store)) if kind == "gold"
           else baseline_adapter_factory(kind))
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "items.jsonl"
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                     encoding="utf-8")
        return run_task(REPO / "tasks" / "cit_validity", p, fac, store)


@pytest.fixture(scope="module")
def store():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.lawkb.store import LawkbStore

    return LawkbStore.load(REPO / "lawkb")


def test_c363_ct_草稿_gold_自证满分(store):
    rows = _bleached_rows()
    run = _run_kind("gold", store, rows)
    assert run.mean == 100.0
    assert all(r.display == "100.00" for r in run.results)


def test_c364_ct_草稿_rules_泄题门禁与陷阱窗全零(store):
    rows = _bleached_rows()
    run = _run_kind("rules", store, rows)
    scores = {r.item_id: float(r.display) for r in run.results}
    # 陷阱窗全零：rules 只会答 ok，判别非 ok 状态是本轴全部考点
    for did in ("ct-201", "ct-202", "ct-203", "ct-210"):
        assert scores[did] == 0.0, f"{did} 陷阱窗被 rules 得分 {scores[did]}（泄题嫌疑）"
    # 对照窗：ok 判定 rules 应满分（题面无隐藏门槛）
    assert scores["ct-211"] == 100.0
    # 均分门禁（20.00）：抬升即泄题前兆
    assert run.mean <= 40.0, f"rules 均分 {run.mean} 异常抬升（泄题前兆，c161 同纪律）"

# -*- coding: utf-8 -*-
"""c179：确定性金样——同一输入两次 run_tasks 逐题分全等（pass^k 的前提）。

pass^k 组合语义假设同一考生同一题重跑同分（机检翻转仅来自采样温度）；
若管线内部存在隐藏随机源（集合迭代、并发归并、浮点求和顺序），本测试
先于论文实验抓住它。并发（max_workers>1）与串行两条路径都锁。
"""

from pathlib import Path

from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.adapters.mock import mock_gold_adapter
from cnjudbench.runner.evaluate import run_tasks

REPO = Path(__file__).resolve().parents[1]
TASKS = ("cit_validity", "s_charge_subsume", "contract_risk")


def _jobs():
    return [(t, REPO / "tasks" / t, REPO / "data" / "public" / f"{t}.jsonl")
            for t in TASKS]


def _scores(runs) -> dict:
    return {(run.task_id, r.item_id): r.score
            for run in runs for r in run.results}


def test_mock_gold_serial_deterministic():
    store = LawkbStore.load(REPO / "lawkb")
    r1 = _scores(run_tasks(_jobs(), lambda item: mock_gold_adapter(item, store), store))
    r2 = _scores(run_tasks(_jobs(), lambda item: mock_gold_adapter(item, store), store))
    assert r1 == r2
    assert r1 and all(v is not None for v in r1.values())


def test_mock_gold_concurrent_deterministic():
    store = LawkbStore.load(REPO / "lawkb")
    serial = _scores(run_tasks(_jobs(), lambda item: mock_gold_adapter(item, store), store))
    concurrent = _scores(run_tasks(_jobs(), lambda item: mock_gold_adapter(item, store),
                                   store, max_workers=4))
    assert serial == concurrent  # 并发不改变任何一题的判分结果

# -*- coding: utf-8 -*-
"""R31 草稿隔离与判分预检机检（c361-c362）。

- c361：判分管线只读 data/public（drafts/FRAMEWORK 草稿章程的硬声明）——
  load_all_items 的输出不得含任何草稿 id 或 split!='public'；
- c362：ct 草稿的判分面预检——把隔离字段漂洗成合法 Item 后走正式
  run_task + mock:gold 链，必须满分自证。真考生轮跑之前即可发现
  gold/predicates_ref/锚配置错误（漂洗仅内存内进行，不回写草稿文件）。
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


def test_c361_判分管线不消费草稿():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.sample import load_all_items

    draft_ids = set()
    for p in (REPO / "data" / "drafts").rglob("*.json"):
        if p.name != "README.md":
            draft_ids.add(json.loads(p.read_text(encoding="utf-8"))["id"])
    assert draft_ids, "草稿目录为空？"

    items = load_all_items()
    assert items, "public 集为空？"
    clash = sorted({it.id for it in items} & draft_ids)
    assert not clash, f"草稿 id 泄入判分管线: {clash}"
    bad_split = [it.id for it in items if it.split != "public"]
    assert not bad_split, f"非 public split 进判分管线: {bad_split}"
    stray = list((REPO / "data" / "drafts").glob("*.jsonl"))
    assert not stray, \
        f"drafts 目录出现 jsonl 会被 load_all_items 之外的路径误读: {stray}"


@pytest.mark.parametrize("did", DRAFT_IDS)
def test_c362_ct_草稿判分面自证满分(did):
    sys.path.insert(0, str(REPO / "src"))
    from pathlib import Path as _P

    from cnjudbench.adapters.mock import mock_gold_adapter
    from cnjudbench.lawkb.store import LawkbStore
    from cnjudbench.runner.evaluate import run_task
    from cnjudbench.schemas.item import Item

    d = json.loads((REPO / "data" / "drafts" / "cit_validity" / f"{did}.json")
                   .read_text(encoding="utf-8"))
    assert d["draft"] is True, f"{did} 草稿标记丢失（隔离红线）"
    # 漂洗：仅去隔离字段 + 合法化 canary/split（内存内，不回写）
    for k in ("draft", "draft_status", "draft_notes"):
        d.pop(k, None)
    d["canary"] = f"CNJB-CANARY-{hashlib.md5(d['id'].encode()).hexdigest()[:4]}"
    d["split"] = "public"
    item = Item.model_validate(d)

    store = LawkbStore.load(REPO / "lawkb")
    with tempfile.TemporaryDirectory() as td:
        items_path = _P(td) / "items.jsonl"
        items_path.write_text(json.dumps(d, ensure_ascii=False) + "\n",
                              encoding="utf-8")
        run = run_task(REPO / "tasks" / d["task_id"], items_path,
                       lambda it: mock_gold_adapter(it, store), store)
    assert run.results and run.results[0].item_id == did
    r = run.results[0]
    assert r.score is not None, f"{did}: {r.error}"
    assert r.display == "100.00", \
        f"{did} 判分面自证失败（金样 {r.display}≠100.00）：考生轮前须修配置"

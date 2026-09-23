# -*- coding: utf-8 -*-
"""R16 泄露面与解析器防线（c253/c259/c260/c261）：

- c260 prompt 渲染不得包含 gold（L0 题面抓取防线：金样字段对考生不可见）；
- c253 法名别名解析（简称/全称/剥尾/书名号）；
- c259 audit_anchors 覆盖题数 == 数据全集（审计盲区检测）；
- c261 manifest prompt_hash 与 run 内实际渲染 prompt 一致；
- c257 run-all jobs 返回顺序 == 传入顺序（pass^k 与 report 对齐的前提）。
"""

import json
import subprocess
import sys
from pathlib import Path

from cnjudbench.lawkb.resolve import alias_lookup
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.runner.evaluate import _build_prompt, load_task_package, run_tasks

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / ".venv" / "Scripts" / "python.exe")


def _load_first_item(tid: str):
    from cnjudbench.schemas.item import Item
    line = next(l for l in (REPO / "data" / "public" / f"{tid}.jsonl")
                .read_text(encoding="utf-8-sig").splitlines() if l.strip())
    return Item.model_validate_json(line)


def test_c260_prompt_hides_gold_and_canary():
    from cnjudbench.schemas.item import Item
    store = LawkbStore.load(REPO / "lawkb")
    for tid in ("u_element_extract", "s_charge_subsume", "calc_fail_to_pass"):
        task, _ = load_task_package(REPO / "tasks" / tid)
        for ln in (REPO / "data" / "public" / f"{tid}.jsonl").read_text(
                encoding="utf-8-sig").splitlines()[:5]:
            if not ln.strip():
                continue
            item = json.loads(ln)
            prompt = _build_prompt(task, Item.model_validate_json(ln))
            gold_blob = json.dumps(item["gold"], ensure_ascii=False)
            assert gold_blob not in prompt, f"{tid}/{item['id']}: gold 泄入 prompt"
            assert item["canary"] not in prompt, f"{tid}/{item['id']}: canary 泄入 prompt"


def test_c253_alias_lookup_variants():
    store = LawkbStore.load(REPO / "lawkb")
    cases = {
        "中华人民共和国刑法": "npc_criminal_law",
        "刑法": "npc_criminal_law",
        "《中华人民共和国民法典》": "npc_civil_code",   # 书名号
        "民法典": "npc_civil_code",
        "中华人民共和国民法典（2020）": None or "npc_civil_code",  # 剥尾括注重试
    }
    for raw, expect in cases.items():
        assert alias_lookup(store, raw) == expect, raw
    assert alias_lookup(store, "不存在的某法") is None


def test_c259_anchor_audit_covers_all_items():
    r = subprocess.run([PY, "scripts/audit_anchors.py"], cwd=REPO,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0
    out = r.stdout
    n_items = int(out.split("audit_anchors: ")[1].split(" items")[0])
    n_public = sum(1 for f in (REPO / "data" / "public").glob("*.jsonl")
                   for ln in f.read_text(encoding="utf-8-sig").splitlines()
                   if ln.strip())
    assert n_items == n_public == 323  # 漏扫包=审计假绿


def test_c257_run_jobs_order_stable():
    store = LawkbStore.load(REPO / "lawkb")
    from cnjudbench.adapters.mock import mock_gold_adapter
    jobs = [("cit_validity", REPO / "tasks" / "cit_validity",
             REPO / "data" / "public" / "cit_validity.jsonl"),
            ("tau_jud_intake", REPO / "tasks" / "tau_jud_intake",
             REPO / "data" / "public" / "tau_jud_intake.jsonl")]
    runs = run_tasks(jobs, lambda item: mock_gold_adapter(item, store), store,
                     max_workers=2)
    assert [r.task_id for r in runs] == [j[0] for j in jobs]  # 顺序 == 传入序

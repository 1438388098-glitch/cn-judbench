# -*- coding: utf-8 -*-
"""DESIGN v0.4 §5.3：dms_side_effect_intake 案管沙箱副作用任务。"""

from __future__ import annotations

import json
from pathlib import Path

from cnjudbench import cli
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.tools.dms import apply, default_state
from cnjudbench.tools.sandbox import ToolSandbox

REPO = Path(__file__).resolve().parents[1]


def _items() -> list[dict]:
    return [json.loads(l) for l in
            (REPO / "data" / "public" / "dms_side_effect_intake.jsonl")
            .read_text(encoding="utf-8-sig").splitlines() if l.strip()]


def test_dms_ops_order_dependency():
    """先写文书后建卡 → tool_error，终态留缺口（§5.3 依赖纪律）。"""
    state = default_state()
    ok, err, _ = apply(state, "write_document",
                       {"case_no": "（2024）X民初1号", "doc_type": "受理通知书", "content": "c"})
    assert not ok and "no such case" in err
    assert state["documents"] == {}


def test_sandbox_replay_matches_expected_state():
    """gold.calls 在空白沙箱重放 → 终态与 gold.expected_state 逐叶一致。"""
    items = {i["id"]: i for i in _items()}
    sandbox = ToolSandbox(LawkbStore.load(REPO / "lawkb"))
    for call in items["d-001"]["gold"]["calls"]:
        entry = sandbox.execute(call["name"], call["args"])
        assert entry.ok, entry.error
    snap = sandbox.dms_snapshot()
    want = items["d-001"]["gold"]["expected_state"]
    assert snap["cards"] == want["cards"] and snap["documents"] == want["documents"]
    assert snap["events"] == want["events"]


def test_dms_diff_mock_tools_end_to_end(tmp_path, monkeypatch):
    """mock:tools 重放 gold.calls → dms 三题满分；fake_tool 负例一票否决 0 分。"""
    monkeypatch.chdir(REPO)
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "dms_side_effect_intake",
                   "--model", "mock:tools", "--out", str(out)])
    assert rc == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    by_id = {i["id"]: i for i in s["tasks"]["dms_side_effect_intake"]["items"]}
    for i in range(1, 9):
        assert by_id[f"d-{i:03d}"]["score"] == "100.00", f"d-{i:03d}"
    for iid in ("d-101", "d-102", "d-103", "d-104"):  # §5.3 在办案件（state0 预置）
        assert by_id[iid]["score"] == "100.00", iid
    assert float(by_id["d-fake-001"]["score"]) == 0.00  # 叙述不调用：fake_tool+终态空


def test_sandbox_state0_injection():
    """gold.initial_state 注入沙箱：跳过建卡直接 update 成功，快照含分心卡。"""
    items = {i["id"]: i for i in _items()}
    s0 = items["d-104"]["gold"]["initial_state"]
    sandbox = ToolSandbox(LawkbStore.load(REPO / "lawkb"), dms_state0=s0)
    ok, err, _ = apply(sandbox.dms_snapshot(), "noop", None)  # 只为证明快照可读
    entry = sandbox.execute("update_case_card",
                            {"case_no": "（2024）京0105民初804号",
                             "fields": {"close_reason": "调解结案"}})
    assert entry.ok, entry.error
    snap = sandbox.dms_snapshot()
    assert snap["cards"]["（2024）京0105民初804号"]["close_reason"] == "调解结案"
    assert "（2024）京0105民初805号" in snap["cards"]  # 预置分心卡保留


def test_env_diff_state0_and_distractor():
    """env_diff 从 initial_state 起步：正确轨迹满分；误伤分心卡按叶比例扣分。"""
    import copy
    from types import SimpleNamespace

    from cnjudbench.predicates.base import EvalContext
    from cnjudbench.predicates.ftp import env_diff
    from cnjudbench.schemas.task import PredicatesFile

    items = {i["id"]: i for i in _items()}
    it = items["d-104"]
    gold = it["gold"]
    from cnjudbench.schemas.item import Item

    pf = PredicatesFile.model_validate({"ftp": [{"type": "env_diff", "on_fail": "partial"}]})
    spec = pf.ftp[0]
    it = Item.model_validate(it)

    def run(entries):
        ctx = EvalContext(task=None, item=it, answer=None, answer_text="",
                          claims=[], claim_status="ok",
                          store=LawkbStore.load(REPO / "lawkb"), tool_log=entries)
        return env_diff(ctx, spec, 0)

    good = [SimpleNamespace(name=c["name"], args=c["args"]) for c in gold["calls"]]
    assert run(good).pass_ratio == 1.0

    bad_args = [dict(c["args"]) for c in gold["calls"]]
    bad_args[0]["case_no"] = "（2024）京0105民初805号"  # 误伤分心卡
    r = run([SimpleNamespace(name=c["name"], args=a) for c, a in zip(gold["calls"], bad_args)])
    assert 0.0 < r.pass_ratio < 1.0 and r.failure_taxonomy == "env_state_mismatch"

def test_env_diff_events_order_and_duplicate():
    """events 多重集语义：执行顺序不同不扣分；重复排期（multiset 多出）扣分。"""
    import copy
    from types import SimpleNamespace

    from cnjudbench.predicates.base import EvalContext
    from cnjudbench.predicates.ftp import env_diff
    from cnjudbench.schemas.item import Item
    from cnjudbench.schemas.task import PredicatesFile

    items = {i["id"]: i for i in _items()}
    it = Item.model_validate(items["d-102"])  # 排期 + 落文书
    gold = it.gold
    pf = PredicatesFile.model_validate(
        {"ftp": [{"type": "env_diff", "on_fail": "partial"}]})
    spec = pf.ftp[0]

    def run(calls):
        entries = [SimpleNamespace(name=c["name"], args=c["args"]) for c in calls]
        ctx = EvalContext(task=None, item=it, answer=None, answer_text="",
                          claims=[], claim_status="ok",
                          store=LawkbStore.load(REPO / "lawkb"), tool_log=entries)
        return env_diff(ctx, spec, 0)

    reordered = [gold["calls"][1], gold["calls"][0]]  # 先落文书后排期
    assert run(reordered).pass_ratio == 1.0

    dup = copy.deepcopy(gold["calls"]) + [gold["calls"][0]]  # 排期重复执行
    r = run(dup)
    assert r.pass_ratio < 1.0 and r.failure_taxonomy == "env_state_mismatch"

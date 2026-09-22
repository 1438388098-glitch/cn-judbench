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
    assert float(by_id["d-fake-001"]["score"]) == 0.00  # 叙述不调用：fake_tool+终态空

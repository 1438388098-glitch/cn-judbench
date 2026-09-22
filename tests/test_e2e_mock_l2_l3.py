"""P2 e2e：Mock 全流程 L2 + L3a（impl-P2 §8 test_e2e_mock_l2_l3 / DoD 2/4）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from cnjudbench import cli

REPO = Path(__file__).resolve().parents[1]
TWO_DECIMALS = re.compile(r"^\d+\.\d{2}$")


def _summary(out: Path) -> dict:
    return json.loads((out / "summary.json").read_text(encoding="utf-8"))


def test_e2e_l2_mock_tools(tmp_path, monkeypatch):
    """L2 mock:tools：exit 0、分数两位小数、假调用夹具 0.00、轨迹落盘 + hash 进 manifest。"""
    monkeypatch.chdir(REPO)
    out = tmp_path / "l2"
    rc = cli.main(["run-all", "--tasks", "tool_search_statute", "--model", "mock:tools",
                   "--out", str(out)])
    assert rc == 0
    s = _summary(out)
    blk = s["tasks"]["tool_search_statute"]
    assert blk["n"] == 20 and blk["mean"] == "95.00"
    assert all(TWO_DECIMALS.match(it["score"]) for it in blk["items"])
    fake = next(it for it in blk["items"] if it["id"] == "t-fake-001")
    assert fake["score"] == "0.00" and "fake_tool" in fake["taxonomy"]
    assert blk["mean"] == "95.00"  # 19×100 + 1×0

    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    hashes = m["tools"]["trajectory_hashes"]
    assert set(hashes) == {it["id"] for it in blk["items"]}
    assert all(h.startswith("sha256:") for h in hashes.values())
    traj_files = list((out / "items").glob("*.trajectory.json"))
    assert len(traj_files) == 20
    traj = json.loads((out / "items" / "t-ss-001.trajectory.json").read_text(encoding="utf-8"))
    assert traj["calls"][0]["name"] == "search_statute"
    assert traj["calls"][0]["ok"] is True


def test_e2e_l3a_mock_gold(tmp_path, monkeypatch):
    """L3a mock:gold：exit 0、10 题全 100.00、progress 诊断列不触发警报。"""
    monkeypatch.chdir(REPO)
    out = tmp_path / "l3a"
    rc = cli.main(["run-all", "--tasks", "gaia_fee_deadline", "--model", "mock:gold",
                   "--out", str(out)])
    assert rc == 0
    s = _summary(out)
    blk = s["tasks"]["gaia_fee_deadline"]
    assert blk["n"] == 11 and blk["mean"] == "100.00"
    assert s["diagnostics"]["gaia_fee_deadline"]["diag_drop"] == "0.00"
    assert not s["diagnostics"]["gaia_fee_deadline"]["reward_hacking_alert"]


def test_e2e_flip_rate_zero_for_p2_tasks(tmp_path, monkeypatch):
    """P2 全链路 Mock 确定性：复跑逐题全等（轨迹 hash 亦稳定）。"""
    monkeypatch.chdir(REPO)
    outs = []
    for tag in ("a", "b"):
        out = tmp_path / tag
        rc = cli.main(["run-all", "--tasks", "tool_search_statute,gaia_fee_deadline",
                       "--model", "mock:tools", "--out", str(out)])
        assert rc == 0
        outs.append(_summary(out))
    sig_a = [(t, it["id"], it["score"], tuple(it["taxonomy"]))
             for t, blk in outs[0]["tasks"].items() for it in blk["items"]]
    sig_b = [(t, it["id"], it["score"], tuple(it["taxonomy"]))
             for t, blk in outs[1]["tasks"].items() for it in blk["items"]]
    assert sig_a == sig_b

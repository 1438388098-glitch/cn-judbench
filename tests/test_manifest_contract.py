"""DESIGN v0.4 §8 正式分契约：manifest 五块 + provisional 门禁。"""

from __future__ import annotations

import json
from pathlib import Path

from cnjudbench import cli
from cnjudbench.runner.manifest import deps_lock_sha256, mark_provisional

REPO = Path(__file__).resolve().parents[1]


def _run(tmp_path: Path, *extra: str) -> tuple[int, Path]:
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "u_element_extract", "--model", "mock:gold",
                   "--out", str(out), *extra])
    return rc, out


def test_manifest_contract_blocks(tmp_path, monkeypatch):
    """§8：deps/judge/stats/baselines/human_eval 五块齐备；judge 块随 --with-judge 填充。"""
    monkeypatch.chdir(REPO)
    rc, out = _run(tmp_path, "--with-judge", "--judge", "mock", "--k-pass", "2")
    assert rc == 0
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert set(m) >= {"deps", "judge", "stats", "baselines", "human_eval", "provisional"}
    assert m["deps"]["python"]
    assert m["judge"] == {"enabled": True, "model_id": "mock-judge", "mode": "k_pass",
                          "k_pass": 2, "prompt_hash": m["judge"]["prompt_hash"]}
    assert m["judge"]["prompt_hash"]
    assert m["stats"]["n_replicates"] == 1
    assert m["stats"]["ci95"] is not None  # mock:gold 全对，分数恒定 → CI 收窄
    assert m["human_eval"] is None
    # mock:gold 也跑了同管线基线
    assert set(m["baselines"]) == {"random", "rules"}
    assert m["baselines"]["random"] == "0.00"
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["provisional"] == m["provisional"]


def test_provisional_true_without_lock_and_flip(tmp_path, monkeypatch):
    """仓库无锁文件且未复跑测翻转 → provisional（不得进对外对比表）。"""
    monkeypatch.chdir(tmp_path)  # 无任何锁文件
    deps = {"lock_sha256": None, "python": "3.x"}
    stats = {"ci95": None, "flip_rate": None, "n_replicates": 1}
    assert mark_provisional(deps, stats) is True
    # 有锁但仍缺 flip_rate（正式榜要求）→ 仍 provisional
    assert mark_provisional({**deps, "lock_sha256": "sha256:abc"}, stats) is True
    # 齐备才放行
    assert mark_provisional({**deps, "lock_sha256": "sha256:abc"},
                            {**stats, "flip_rate": 0.02}) is False
    # 非正式榜（内部迭代）：锁齐即可
    assert mark_provisional({**deps, "lock_sha256": "sha256:abc"},
                            {**stats, "flip_rate": None}, formal_board=False) is False


def test_deps_lock_sha256_stable_and_hex(tmp_path):
    p = tmp_path / "uv.lock"
    p.write_bytes(b"frozen deps")
    a = deps_lock_sha256(tmp_path)
    assert a and a.startswith("sha256:") and len(a) == len("sha256:") + 64
    assert a == deps_lock_sha256(tmp_path)  # 确定性
    p.write_bytes(b"frozen deps v2")
    assert a != deps_lock_sha256(tmp_path)  # 内容敏感


def test_report_csv_exported(tmp_path, monkeypatch):
    """DESIGN v0.4 §9：run-all 落盘 report.csv，列 = §6.1 主表模板 + provisional。"""
    monkeypatch.chdir(REPO)
    rc, out = _run(tmp_path)
    assert rc == 0
    text = (out / "report.csv").read_text(encoding="utf-8-sig")
    lines = text.strip().splitlines()
    assert lines[0].split(",") == ["模型", "rev", "cap±CI", "hard±CI", "safety", "solve%",
                                   "scored%", "e2e%", "fail2pass%", "recovery%", "$/solve", "p95",
                                   "flip%", "provisional"]  # v0.6：scored% = n/a 率披露列
    assert "100.00" in lines[1]  # mock:gold 满分
    assert lines[1].endswith("True")  # 单跑缺 flip_rate/锁 → provisional 诚实标注
    assert "n/a" in lines[1]  # 工具轨列与 flip% 不编造

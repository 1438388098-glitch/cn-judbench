"""P3 e2e：mock 全流程 + run-dialog + 产物齐全。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_e2e_mock_p3(repo_root: Path, tmp_path: Path):
    py = sys.executable
    env_cwd = str(repo_root)

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [py, "-m", "cnjudbench", *args],
            cwd=env_cwd, capture_output=True, text=True, encoding="utf-8",
        )

    out_c = tmp_path / "c1"
    r1 = run("run", "--task", "contract_risk", "--model", "mock:gold", "--out", str(out_c))
    assert r1.returncode == 0, r1.stdout + r1.stderr
    out_a = tmp_path / "a1"
    r2 = run("run", "--task", "a_irac_reason", "--model", "mock:gold", "--out", str(out_a))
    assert r2.returncode == 0, r2.stdout + r2.stderr
    out_l = tmp_path / "l4"
    r3 = run("run", "--task", "long_horizon_case", "--model", "mock:gold", "--out", str(out_l))
    assert r3.returncode == 0, r3.stdout + r3.stderr

    for d in (out_c, out_a, out_l):
        assert (d / "summary.json").is_file()
        assert (d / "manifest.json").is_file()
        assert (d / "limits.md").is_file()
        s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        assert "本评测不构成法律意见" in s["disclaimer"]
        for row in s["tasks"].values():
            for it in row["items"]:
                assert it["score"] == "n/a" or it["score"].count(".") == 1

    # score–time 列存在且为两位小数或 n/a
    sl = json.loads((out_l / "summary.json").read_text(encoding="utf-8"))
    # long_horizon 走 run，AUC 在 dialog summary；此处仅锁主分格式
    assert sl["tasks"]["long_horizon_case"]["mean"] != "n/a"

    out_t = tmp_path / "tau"
    r4 = run(
        "run-dialog", "--task", "tau_jud_intake", "--model", "mock:dialog",
        "--user-seed", "42", "--k-pass", "2", "--out", str(out_t),
    )
    assert r4.returncode == 0, r4.stdout + r4.stderr
    ts = json.loads((out_t / "summary.json").read_text(encoding="utf-8"))
    assert ts["user_seed"] == 42
    assert ts["model_seed"] is None
    assert ts["stability"]["pass_k_fixed_user_str"]
    assert ts["stability"]["lawyer_baseline"] == "未测"
    assert "user_script_var" in ts["stability"]["variance"]
    assert (out_t / "limits.md").read_text(encoding="utf-8").count("user_seed") >= 1
    dialogs = list((out_t / "items").glob("*.dialog.json")) or list(
        (out_t / "items").glob("*.trajectory.json")
    )
    assert dialogs
    payload = json.loads(dialogs[0].read_text(encoding="utf-8"))
    assert "turns" in payload and payload["n_turns"] >= 1

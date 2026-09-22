# -*- coding: utf-8 -*-
"""论文表生成与 flip 门禁（DESIGN v0.4 §6.1/§8/§9）。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from make_paper_tables import _row_from_summary, build_tables  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def test_row_from_summary_gates_safety_and_provisional(tmp_path):
    summary = {
        "run_id": "abc123", "model_id": "glm", "provisional": True,
        "capability": {"grand_eq": "91.07", "hard": "85.00",
                       "hard_ci95": ["80.00", "90.00"]},
        "safety_score": "0.00",
        "baselines": {"random": {"grand_eq": "0.00"}, "rules": {"grand_eq": "44.19"}},
        "cost": {"dollar_per_solve": None, "pass_k": None},
        "tasks": {"u": {"items": [{"role": "capability", "score": "100.00"},
                                  {"role": "capability", "score": "40.00"},
                                  {"role": "safety", "score": "0.00"},
                                  {"role": "capability", "score": "n/a"}]}},
    }
    row = _row_from_summary(summary)
    assert row["solve%"] == "50.00"          # 2/2 计分能力题过线；safety 与 n/a 不进分母
    assert row["hard±CI"] == "85.00 [80.00,90.00]"
    assert row["$/solve"] == "n/a"           # 无价目禁编造
    assert row["provisional"] == "True"


def test_build_tables_splits_main_and_provisional(tmp_path):
    runs = tmp_path / "runs"
    for rid, prov in (("r1", True), ("r2", False)):
        d = runs / rid
        d.mkdir(parents=True)
        (d / "summary.json").write_text(json.dumps({
            "run_id": rid, "model_id": "m", "provisional": prov,
            "capability": {"grand_eq": "60.00"}, "safety_score": "n/a",
            "baselines": {}, "cost": {}, "tasks": {},
        }, ensure_ascii=False), encoding="utf-8")
    text, n_main, n_prov = build_tables(runs)
    assert (n_main, n_prov) == (1, 1)
    assert "r2" in text.split("T-provisional")[0]   # r2 进正式表
    assert "r1" in text.split("T-provisional")[1]   # r1 进附录


def test_flip_rate_check_smoke_mock_zero():
    """离线 mock 复跑翻转率必须为 0（impl-P1-rest §5；v0.4 判分管线回归）。"""
    rc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "flip_rate_check.py"),
         "--tasks", "u_element_extract", "--model", "mock:gold"],
        cwd=REPO, capture_output=True, text=True, timeout=300)
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "0.00" in rc.stdout or "flip" in rc.stdout.lower()

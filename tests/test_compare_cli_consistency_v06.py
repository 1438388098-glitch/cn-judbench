# -*- coding: utf-8 -*-
"""c189：compare CLI 人读输出与 --out JSON 返回数字一致（防双口径漂移）。"""

import io
import json
import re
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from cnjudbench.cli import main

REPO = Path(__file__).resolve().parents[1]
RUN_A = REPO / "reports" / "runs" / "v05new-s1m-score"
RUN_B = REPO / "reports" / "runs" / "v05new-s2m-score"


def test_c189_cli_print_matches_out_json(tmp_path):
    if not ((RUN_A / "summary.json").is_file() and (RUN_B / "summary.json").is_file()):
        pytest.skip("E17 双考生 run 目录缺失")
    out_json = tmp_path / "cmp.json"
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["compare", "--run-a", str(RUN_A), "--run-b", str(RUN_B),
                   "--out", str(out_json)])
    assert rc == 0
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    printed = buf.getvalue()

    m = re.search(r"mean_a=([\d.]+) mean_b=([\d.]+) diff=([-\d.]+)", printed)
    assert m, f"stdout 缺 mean/diff 行：{printed[:200]}"
    assert float(m.group(1)) == round(doc["mean_a"], 2)
    assert float(m.group(2)) == round(doc["mean_b"], 2)
    assert float(m.group(3)) == round(doc["paired_ci"]["point"], 2)

    ci = doc["paired_ci"]
    m_ci = re.search(r"\[([-\d.]+), ([-\d.]+)\]", printed)
    assert m_ci
    assert (float(m_ci.group(1)), float(m_ci.group(2))) == (
        round(ci["ci95_low"], 2), round(ci["ci95_high"], 2))

# -*- coding: utf-8 -*-
"""DESIGN v0.4 §9：dashboard payload 携带 capability/safety/baselines/provisional。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sync_dashboard import build_payload  # noqa: E402


def test_payload_carries_v04_columns(tmp_path):
    summary = {
        "run_id": "abc123",
        "model_id": "mock:gold",
        "temperature": 0.0,
        "provisional": True,
        "capability": {"grand_eq": "91.07", "hard": "85.00", "n_hard": 28},
        "safety_score": "0.00",
        "baselines": {"random": {"grand_eq": "0.00"}, "rules": {"grand_eq": "44.19"}},
        "per_task": {"u_element_extract": {"machine_mean": 91.07, "n_machine": 43}},
    }
    payload = build_payload(summary, tmp_path / "summary.json")
    m = payload["metrics"]
    assert m["capability"]["hard"] == "85.00"
    assert m["safety_score"] == "0.00"
    assert m["baselines"]["rules"]["grand_eq"] == "44.19"
    assert m["provisional"] is True


def test_payload_defaults_honest_when_absent(tmp_path):
    payload = build_payload({"per_task": {}}, tmp_path / "s.json")
    assert payload["metrics"]["safety_score"] == "n/a"
    assert payload["metrics"]["baselines"] == {}
    assert payload["metrics"]["provisional"] is True  # 缺声明默认 provisional

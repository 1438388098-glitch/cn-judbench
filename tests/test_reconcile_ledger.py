# -*- coding: utf-8 -*-
"""round-23（c447）：reconcile_ledger 直测——合成账本/run 夹具，锁定
「只报差异不改账」与 --strict 退出语义。"""

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "reconcile_ledger", REPO / "scripts" / "reconcile_ledger.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mk_ledger(tmp_path: Path, rows: str) -> Path:
    p = tmp_path / "ledger.md"
    p.write_text(
        "# 账本\n\n## 1. 主记分板\n\n| # | run | 模型 | 成色 | grand_eq |\n"
        "|---|---|---|---|---|\n" + rows + "\n\n## 2. 其他\n", encoding="utf-8")
    return p


def _mk_run(tmp_path: Path, run: str, grand: float) -> None:
    d = tmp_path / "runs" / run
    d.mkdir(parents=True)
    (d / "summary.json").write_text(
        json.dumps({"capability": {"grand_eq": grand}}, ensure_ascii=False),
        encoding="utf-8")


def test_reconcile_all_match_reports_ok(tmp_path, capsys):
    mod = _load()
    ledger = _mk_ledger(tmp_path, '| 1 | `run-a` | 模型甲（默认） | 洁净隔离 | **59.14** |\n')
    _mk_run(tmp_path, "run-a", 59.14)
    rc = mod.main(["--ledger", str(ledger), "--runs-root", str(tmp_path / "runs"), "--strict"])
    assert rc == 0 and "RECONCILE: OK" in capsys.readouterr().out


def test_reconcile_detects_mismatch_report_only(tmp_path, capsys):
    mod = _load()
    ledger = _mk_ledger(tmp_path, '| 1 | `run-a` | 模型甲（默认） | 洁净隔离 | **59.14** |\n')
    _mk_run(tmp_path, "run-a", 68.72)
    rc = mod.main(["--ledger", str(ledger), "--runs-root", str(tmp_path / "runs")])  # 报告模式：有差异也 0 退出
    out = capsys.readouterr().out
    assert rc == 0 and "DIFF run-a: 账面 59.14 ≠ 产物 68.72" in out


def test_reconcile_strict_blocks_on_diff_and_missing(tmp_path, capsys):
    mod = _load()
    ledger = _mk_ledger(tmp_path,
                        '| 1 | `run-a` | 模型甲（默认） | 洁净隔离 | **59.14** |\n'
                        '| 2 | `run-b` | 模型乙（高） | API 隔离 | **64.18** |\n')
    _mk_run(tmp_path, "run-a", 10.0)  # run-b 缺 summary
    rc = mod.main(["--ledger", str(ledger), "--runs-root", str(tmp_path / "runs"), "--strict"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "DIFF run-a" in out and "MISSING run-b" in out

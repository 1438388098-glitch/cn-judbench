# -*- coding: utf-8 -*-
"""c169：audit_anchors 硬失败路径——tmp items 目录驱动 main()，不碰仓库 data。"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_anchors  # noqa: E402


def _write_item(root: Path, item: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "zz_fake_package.jsonl").write_text(
        json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")


def _run_main(monkeypatch, items_root: Path) -> int:
    argv = ["audit_anchors.py", "--items-root", str(items_root)]
    monkeypatch.setattr(sys, "argv", argv)
    return audit_anchors.main()


def test_hard_fail_on_not_yet_effective_anchor(tmp_path, monkeypatch, capsys):
    # 刑法264 首版 1997-10-01 生效；as_of=1990 → not_yet_effective → 硬失败
    item = {
        "id": "zz-audit-001",
        "as_of": "1990-01-01",
        "law_anchors": [
            {"law": "中华人民共和国刑法", "article": "264", "effective_on": "1990-01-01"},
        ],
        "gold": {"citations": []},
    }
    _write_item(tmp_path, item)
    rc = _run_main(monkeypatch, tmp_path)
    assert rc == 1
    out = capsys.readouterr().out
    assert "HARD FAIL" in out
    assert "zz-audit-001" in out
    assert "not_yet_effective" in out
    assert "audit_anchors: FAIL" in out


def test_ok_anchor_passes(tmp_path, monkeypatch, capsys):
    # 同一条文 as_of=2015 在窗（cl_264_2011）→ 审计应 OK
    item = {
        "id": "zz-audit-002",
        "as_of": "2015-01-01",
        "law_anchors": [
            {"law": "中华人民共和国刑法", "article": "264", "effective_on": "2015-01-01"},
        ],
        "gold": {"citations": []},
    }
    _write_item(tmp_path, item)
    rc = _run_main(monkeypatch, tmp_path)
    assert rc == 0
    assert "audit_anchors: OK" in capsys.readouterr().out


def test_empty_items_root_ok(tmp_path, monkeypatch, capsys):
    rc = _run_main(monkeypatch, tmp_path)
    assert rc == 0
    assert "audit_anchors: OK" in capsys.readouterr().out


def test_gold_citation_anchor_also_audited(tmp_path, monkeypatch, capsys):
    # 锚不只在 law_anchors：gold.citations 同样逐条审计
    item = {
        "id": "zz-audit-003",
        "as_of": "1990-06-01",
        "gold": {
            "citations": [
                {"law": "中华人民共和国刑法", "article": "264",
                 "as_of": "1990-06-01"},
            ],
        },
    }
    _write_item(tmp_path, item)
    rc = _run_main(monkeypatch, tmp_path)
    assert rc == 1
    out = capsys.readouterr().out
    assert "gold.citations" in out and "zz-audit-003" in out

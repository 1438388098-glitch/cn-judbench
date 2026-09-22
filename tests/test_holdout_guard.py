"""P1 收尾：holdout 守卫（impl-P1-rest §6 test_holdout_guard）。

holdout 路径/题面进入评测输入 → 拒读，退出码 ≠ 0（实现取 2，区别于判分失败 1）。
"""

from __future__ import annotations

import json
from pathlib import Path

from cnjudbench import cli
from cnjudbench.runner.guards import HoldoutPathError, assert_items_not_holdout, assert_no_holdout

REPO = Path(__file__).resolve().parents[1]


def test_holdout_path_rejected_with_exit_2(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO)
    rc = cli.main(["run", "--task", "cit_validity", "--model", "mock:gold",
                   "--items-root", "data/holdout", "--out", str(tmp_path / "r")])
    assert rc == 2


def test_holdout_split_item_rejected_with_exit_2(tmp_path, monkeypatch):
    """题面 split=holdout 即使路径不在 holdout 目录，也禁止进 prompt。"""
    monkeypatch.chdir(REPO)
    line = (REPO / "data" / "public" / "cit_validity.jsonl").read_text(
        encoding="utf-8").splitlines()[0]
    item = json.loads(line)
    item["split"] = "holdout"
    root = tmp_path / "items"
    root.mkdir()
    (root / "cit_validity.jsonl").write_text(
        json.dumps(item, ensure_ascii=False), encoding="utf-8")
    rc = cli.main(["run", "--task", "cit_validity", "--model", "mock:gold",
                   "--items-root", str(root), "--out", str(tmp_path / "r")])
    assert rc == 2


def test_guard_unit_levels():
    assert_no_holdout("data/public", "tasks/cit_validity")  # 不抛
    import pytest
    with pytest.raises(HoldoutPathError):
        assert_no_holdout("data/holdout/secret.jsonl")
    with pytest.raises(HoldoutPathError):
        assert_no_holdout("runs/holdout")

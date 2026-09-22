"""P1 收尾：limits.md 随 run 落盘且含固定段（impl-P1-rest §6 test_limits_written）。"""

from __future__ import annotations

from pathlib import Path

from cnjudbench import cli

REPO = Path(__file__).resolve().parents[1]


def _limits_text(tmp_path: Path, *extra: str) -> str:
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "cit_validity", "--model", "mock:gold",
                   "--out", str(out), *extra])
    assert rc == 0
    path = out / "limits.md"
    assert path.is_file(), "limits.md 必须随 run 落盘"
    return path.read_text(encoding="utf-8")


def test_limits_written_with_fixed_sections(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO)
    md = _limits_text(tmp_path, "--with-judge", "--judge", "mock")
    assert "不构成法律意见" in md  # DISCLAIMER（§12.1 固定段）
    assert "谓词翻转率" in md
    assert "unknown_in_lawkb 分列数" in md
    assert "Min-K%" in md  # 污染检测边界声明


def test_limits_records_judge_identity_and_kpass(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO)
    md = _limits_text(tmp_path, "--with-judge", "--judge", "mock",
                      "--judge-id", "mock-judge-ci", "--k-pass", "2")
    assert "mock-judge-ci" in md
    assert "k_pass=2" in md
    assert "prompt_hash=sha256:" in md  # Judge 偏置可追溯


def test_limits_written_for_machine_only_run(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO)
    md = _limits_text(tmp_path)
    assert "未启用 Judge" in md

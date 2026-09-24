"""P1 收尾：--with-judge 进 runner、机检/Judge 分列、judge_calls 计次（impl-P1-rest §3/§6）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cnjudbench import cli

REPO = Path(__file__).resolve().parents[1]


def _run(tmp_path: Path, tasks: str, *extra: str) -> tuple[int, Path]:
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", tasks, "--model", "mock:gold",
                   "--out", str(out), *extra])
    return rc, out


def _load(out: Path, name: str) -> dict:
    return json.loads((out / name).read_text(encoding="utf-8"))


def test_with_judge_split_columns(tmp_path, monkeypatch):
    """机检/Judge 分列；默认 parallel 禁止出现混合 combined 列。"""
    monkeypatch.chdir(REPO)
    rc, out = _run(tmp_path, "u_element_extract", "--with-judge", "--judge", "mock")
    assert rc == 0
    s = _load(out, "summary.json")
    pt = s["per_task"]["u_element_extract"]
    assert set(pt) >= {"machine_mean_str", "judge_mean_str", "n_machine", "n_judge"}
    assert pt["machine_mean_str"] == "100.00"  # mock:gold 抽样层全对
    assert pt["judge_mean_str"] == "50.00"  # MockJudge 中点确定性给分
    assert pt["n_machine"] == pt["n_judge"] >= 10
    assert "combined_str" not in pt  # --blend 默认 parallel，禁止未标注混分数
    # 题级 judge 列
    assert all(it["judge"] == "50.00" for it in s["tasks"]["u_element_extract"]["items"])


def test_judge_calls_counted_even_for_mock(tmp_path, monkeypatch):
    """规则 2：judge_calls 进 manifest，Mock 也计次 = 题数 × k_pass。"""
    monkeypatch.chdir(REPO)
    rc, out = _run(tmp_path, "u_element_extract", "--with-judge", "--judge", "mock", "--k-pass", "2")
    assert rc == 0
    m = _load(out, "manifest.json")
    assert m["accounting"]["judge_calls"] == m["dataset"]["item_count"] * 2
    assert m["accounting"]["judge_prompt_tokens"] == 0  # Mock 无 token，禁编造
    assert m["accounting"]["judge_completion_tokens"] == 0


def test_no_rubric_task_judge_is_na_not_zero(tmp_path, monkeypatch):
    """规则 3：缺 rubric → judge 列 n/a（禁止填 0.00 充数）。"""
    monkeypatch.chdir(REPO)
    rc, out = _run(tmp_path, "cit_validity", "--with-judge", "--judge", "mock")
    assert rc == 0
    s = _load(out, "summary.json")
    pt = s["per_task"]["cit_validity"]
    assert pt["judge_mean_str"] == "n/a"
    assert pt["n_judge"] == 0
    assert pt["machine_mean_str"] == "100.00"  # mock:gold 抽样层全对
    assert all(it["judge"] == "n/a" for it in s["tasks"]["cit_validity"]["items"])


def test_blend_weighted_is_explicit_only(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO)
    rc, out = _run(tmp_path, "u_element_extract", "--with-judge", "--judge", "mock",
                   "--blend", "weighted")
    assert rc == 0
    pt = _load(out, "summary.json")["per_task"]["u_element_extract"]
    # 0.7×100 + 0.3×50 = 85.00；显式加权才允许出现 combined
    assert pt["combined_str"] == "85.00"


def test_openai_judge_rejected_for_mock_model(monkeypatch):
    monkeypatch.chdir(REPO)
    with pytest.raises(SystemExit, match="mock"):
        cli.main(["run", "--task", "cit_validity", "--model", "mock:gold",
                  "--with-judge", "--judge", "openai"])


def test_machine_only_run_still_clean(tmp_path, monkeypatch):
    """不开启 --with-judge：judge_calls 恒 0，summary 段齐备但 judge 列 n/a。"""
    monkeypatch.chdir(REPO)
    rc, out = _run(tmp_path, "u_element_extract")
    assert rc == 0
    s = _load(out, "summary.json")
    assert s["per_task"]["u_element_extract"]["judge_mean_str"] == "n/a"
    m = _load(out, "manifest.json")
    assert m["accounting"]["judge_calls"] == 0


def test_judge_column_excludes_safety_fixtures(tmp_path, monkeypatch):
    """c373：judge 列与 machine 列同口径剔除 safety 夹具（s 包 13 能力 + 7 安全）。

    构造 13 道 capability（机检 100 / judge 50）+ 7 道 safety（机检 0 / judge 100）：
    修复前 judge 列把 7 道 safety 混入分母（n=20、均值 67.50），与 machine 列（n=13）不可比。
    """
    from cnjudbench.runner.account import Accountant
    from cnjudbench.runner.evaluate import ItemResult, TaskRun

    monkeypatch.chdir(REPO)
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "s_charge_subsume", "--model", "mock:gold",
                   "--out", str(out)])
    assert rc == 0
    manifest = _load(out, "manifest.json")
    args = cli._build_parser().parse_args([
        "run-all", "--tasks", "s_charge_subsume", "--model", "mock:gold",
        "--out", str(out), "--with-judge", "--judge", "mock"])
    cap = [ItemResult(item_id=f"s-{i:03d}", score=100.0, display="100.00")
           for i in range(1, 14)]
    saf = [ItemResult(item_id=f"s-{i:03d}", score=0.0, display="0.00", role="safety")
           for i in range(15, 22)]
    runs = [TaskRun(task_id="s_charge_subsume", results=cap + saf)]

    class JR:
        def __init__(self, mapped: float) -> None:
            self.mapped = mapped
            self.mapped_str = f"{mapped:.2f}"

    judge_scores = {
        "s_charge_subsume": {
            **{f"s-{i:03d}": JR(50.0) for i in range(1, 14)},
            **{f"s-{i:03d}": JR(100.0) for i in range(15, 22)},
        },
    }
    s = cli._build_summary(args, runs, manifest, Accountant(), judge_scores, baseline_runs=None)
    pt = s["per_task"]["s_charge_subsume"]
    assert pt["n_machine"] == 13
    assert pt["n_judge"] == 13
    assert pt["judge_mean_str"] == "50.00"

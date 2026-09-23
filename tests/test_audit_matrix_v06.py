# -*- coding: utf-8 -*-
"""R19 自证矩阵与论文口径审计（c282-c288/c291）：

- c282 E18 预注册剔除集可由 items[].task 逐行重算（无人工挑选空间）；
- c283 requirements-freeze ⊇ pyproject 依赖（deps 锁完整性）；
- c284 全仓 yaml 只走 safe_load（禁 unsafe/full loader）；
- c285 scripts/*.py --help 全覆盖冒烟；
- c286 report.csv §6.1 必报列锁定；
- c287 run-dialog 同 seed 确定性（多轮公平性前提）；
- c288 report 面 canary 扫描（泄露面补 summary/report.csv）；
- c291 dataset-card 难度分布声明与 MANIFEST 逐档对账。
"""

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / ".venv" / "Scripts" / "python.exe")

RUN_A = REPO / "reports" / "runs" / "v05new-s1m-score"
RUN_B = REPO / "reports" / "runs" / "v05new-s2m-score"
CI_RUN = REPO / "reports" / "runs" / "ci"


def test_c282_preregistered_dropped_recomputable():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.metrics.compare import CORE_SIX_TASKS, compare_runs

    out = compare_runs(RUN_A, RUN_B, preregistered=True)
    # 独立重算：task 归属取自 summary 的包键（tasks.<tid>.items[].id），
    # 与判分面解耦——附录表 task 列同源，可逐行核对
    sa = json.loads((RUN_A / "summary.json").read_text(encoding="utf-8"))
    sb = json.loads((RUN_B / "summary.json").read_text(encoding="utf-8"))

    def _load(s):
        task_of, scored = {}, set()
        for tid, t in s.get("tasks", {}).items():
            for it in t.get("items", []):
                if it.get("score") in (None, "n/a"):
                    continue
                task_of[it["id"]] = tid
                if it.get("role", "capability") == "capability":
                    scored.add(it["id"])
        return task_of, scored

    tasks_a, scored_a = _load(sa)
    tasks_b, scored_b = _load(sb)
    common_cap = [i for i in tasks_a if i in tasks_b
                  and i in scored_a and i in scored_b]
    expect_drop = sum(1 for i in common_cap if tasks_a[i] not in CORE_SIX_TASKS)
    assert expect_drop > 0, "E18 对 run 应存在非六包被剔题（否则规则测不到）"
    assert out["n_dropped_by_filter"] == expect_drop
    assert all(tasks_a[it["id"]] in CORE_SIX_TASKS for it in out["items"])
    # 规则已文档化（paper-outline E18 段，透明化无人工挑选空间）
    po = (REPO / "docs" / "paper-outline.md").read_text(encoding="utf-8")
    assert "n_dropped_by_filter" in po and "预注册剔除规则" in po


def test_c283_freeze_covers_pyproject_deps():
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    deps = list(pyproject["project"].get("dependencies") or [])
    deps += (pyproject["project"].get("optional-dependencies") or {}).get("dev", [])

    def norm(name):
        return re.split(r"[\[<>=!~; ]", name.strip(), 1)[0].lower().replace("_", "-")

    freeze = set()
    for line in (REPO / "requirements-freeze.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "==" in line:
            freeze.add(norm(line))
    missing = [d for d in map(norm, deps) if d not in freeze]
    assert not missing, f"requirements-freeze 缺直接依赖：{missing}（升级依赖后须重新 freeze）"


def test_c284_yaml_safe_load_only():
    bad = []
    pat = re.compile(r"yaml\.(unsafe_load|full_load|full_load_all)\b|"
                     r"Loader\s*=\s*yaml\.(UnsafeLoader|FullLoader|Loader)\b")
    for root in ("src", "scripts", "tests"):
        for p in (REPO / root).rglob("*.py"):
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if pat.search(line):
                    bad.append(f"{p.relative_to(REPO)}:{i}")
    assert not bad, f"发现非 safe_load 的 yaml 载入：{bad}"


def _argparse_scripts():
    """只对带 argparse 的脚本做 --help 冒烟。

    数据生成/断言类脚本（add_*.py、assert_run_gate.py 等）无 argparse，
    ``--help`` 会被当作位置参数忽略并**直接执行写仓库的生成逻辑**
    （R19 事故：曾把 data/public 与 lawkb 脏写，见 candidate-285 备注）。
    这类脚本禁止在本测试中执行——新脚本要么带 argparse，要么留在禁测名单外。
    """
    out = []
    for p in sorted((REPO / "scripts").glob("*.py")):
        if "add_argument" in p.read_text(encoding="utf-8", errors="replace"):
            out.append(p.name)
    return out


@pytest.mark.parametrize("script", _argparse_scripts())
def test_c285_scripts_help_smoke(script):
    r = subprocess.run([PY, str(REPO / "scripts" / script), "--help"],
                       cwd=REPO, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"{script} --help 失败：{r.stderr[-300:]}"


def test_c286_report_csv_required_columns():
    if not (CI_RUN / "report.csv").is_file():
        pytest.skip("reports/runs/ci/report.csv 缺失（ci_gate 后生成）")
    import csv

    with (CI_RUN / "report.csv").open(encoding="utf-8-sig") as f:
        header = next(csv.reader(f))
    required = ["模型", "rev", "cap±CI", "hard±CI", "safety", "solve%",
                "scored%", "fail2pass%", "recovery%", "$/solve", "flip%",
                "provisional"]
    missing = [c for c in required if c not in header]
    assert not missing, f"report.csv §6.1 必报列缺失：{missing}"


def test_c287_run_dialog_seed_deterministic(tmp_path):
    outs = []
    for i in (1, 2):
        out = tmp_path / f"d{i}"
        r = subprocess.run(
            [PY, "-m", "cnjudbench", "run-dialog", "--task", "tau_jud_intake",
             "--model", "mock:dialog", "--seed", "7", "--out", str(out)],
            cwd=REPO, capture_output=True, text=True, timeout=600)
        assert r.returncode == 0, r.stderr[-400:]
        s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        outs.append([(it["id"], it["score"]) for it in s["items"]])
    assert outs[0] == outs[1], "同 seed 两跑 items 序列不一致——多轮公平性破坏"


def test_c288_report_surface_canary_scan():
    if not (CI_RUN / "summary.json").is_file():
        pytest.skip("reports/runs/ci 缺失（ci_gate 后生成）")
    for rel in ("summary.json", "report.csv", "manifest.json"):
        text = (CI_RUN / rel).read_text(encoding="utf-8-sig", errors="replace")
        assert "CNJB-CANARY-" not in text, f"{rel} 泄露 canary（canary 只进题面，不进产物）"


def test_c291_dataset_card_difficulty_dist_matches_manifest():
    man = json.loads((REPO / "data" / "public" / "MANIFEST.json")
                     .read_text(encoding="utf-8"))
    dist = {}
    for pkg in man["packages"].values():
        for it in pkg["items"].values():
            d = it.get("difficulty")
            dist[d] = dist.get(d, 0) + 1
    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    m = re.search(r"1 基础 (\d+) 题 / 2 基础-中 (\d+) / 3 中 (\d+) / 4 难 (\d+)", card)
    assert m, "dataset-card 难度分布行缺失或格式变更"
    declared = {1: int(m.group(1)), 2: int(m.group(2)),
                3: int(m.group(3)), 4: int(m.group(4))}
    for lvl in (1, 2, 3, 4):
        assert dist.get(lvl, 0) == declared[lvl], \
            f"难度 {lvl} 档：卡声明 {declared[lvl]} vs 实际 {dist.get(lvl, 0)}"
    assert sum(dist.values()) == man["n_items_total"]

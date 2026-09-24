# -*- coding: utf-8 -*-
"""R9 红线锁定（c190/c188）：

- c190 缺 Judge 时 per_task.judge_mean_str 必为 'n/a' 且 n_judge=0
  （协议红线：缺 Judge 写 n/a，禁填 0.00）；
- c188 README 快速开始中的 mock:gold 示例命令逐条可跑（防文档命令漂移）。
"""

import argparse
import re
import shutil
import subprocess
from pathlib import Path

from cnjudbench.adapters.mock import mock_gold_adapter
from cnjudbench.cli import _build_summary
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.runner.account import Accountant
from cnjudbench.runner.evaluate import run_tasks

REPO = Path(__file__).resolve().parents[1]


def test_c190_judge_na_discipline(tmp_path):
    store = LawkbStore.load(REPO / "lawkb")
    tid = "s_charge_subsume"
    runs = run_tasks([(tid, REPO / "tasks" / tid, REPO / "data" / "public" / f"{tid}.jsonl")],
                     lambda item: mock_gold_adapter(item, store), store)
    args = argparse.Namespace(blend="parallel", n_boot=50, seed=1, ngram_size=13,
                              ngram_corpus=None, user_seed=None, model="mock:gold",
                              temperature=0.0, concurrency=1, with_judge=False,
                              judge="mock", k_pass=2)
    manifest = {"harness_sha": "test", "run_id": "test-run",
                "model": {"model_id": "mock", "revision": None},
                "created_at": "2026-09-23T00:00:00+00:00",
                "temperature": 0.0, "seed": None, "user_seed": None, "tasks": {},
                "with_judge": False, "blend": "parallel",
                "lawkb": {"slice_union_hash": "sha256:x", "store_version": "test",
                          "resolution": "as_of", "as_of_used": []}}
    summary = _build_summary(args, runs, manifest, Accountant(), {})
    pt = summary["per_task"][tid]
    assert pt["judge_mean_str"] == "n/a"     # 缺 Judge → n/a
    assert pt["n_judge"] == 0
    assert pt["judge_mean_str"] != "0.00"    # 红线：禁填 0.00
    assert summary["cost"]["judge_calls"] == 0


def test_c188_readme_mock_commands_runnable(tmp_path):
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    # 抓取 README 中的 mock 示例命令（先归一 CRLF，再折叠 \ 续行）
    joined = readme.replace("\r\n", "\n").replace("\\\n", " ")
    raw_cmds = re.findall(r"((?:\.venv/Scripts/ )?python -m cnjudbench [^\n]*"
                          r"--model mock:(?:gold|tools)[^\n]*)", joined)
    assert raw_cmds, "README 中未找到 mock 示例命令——示例被移除时请同步本测试"
    py = REPO / ".venv" / "Scripts" / "python.exe"
    for i, cmd in enumerate(raw_cmds):
        cmd = cmd.replace(".venv/Scripts/ ", "").replace("python -m", f'"{py}" -m')
        cmd = cmd.rstrip("\\").rstrip()  # 续行折叠兜底
        # 示例输出统一重定向到 tmp（含未写 --out 的命令），避免污染仓库
        if "--out" in cmd:
            cmd = re.sub(r"(--out\s+)\S+", lambda mm: mm.group(1) + str(tmp_path / f"out{i}"), cmd)
        else:
            cmd += f" --out {tmp_path / f'out{i}'}"
        r = subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        assert r.returncode == 0, f"README 命令失败：{cmd}\n{r.stderr[-500:]}"

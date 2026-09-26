# -*- coding: utf-8 -*-
"""R18 发布配套与防御性机检（c272-c280）：

- c272 CHANGELOG 覆盖当前包版本；
- c273+c280 CLI 产物契约：summary.json 含 schema_version 与论文表列依赖的
  字段集（per_task/baselines/provisional）；
- c274 dataset-card §2 包构成表 == MANIFEST n_items 行级；
- c275 密钥不泄面：AdapterError 消息与缓存文件不含 api_key 值；
- c276 docs/README.md 全收录 docs/*.md；
- c277 cost_ledger.pricing_source（有价目→出处；无价目→null 禁编造）；
- c278 scripts/reproduce_paper.sh 一键复现冒烟；
- c279 run_tasks max_workers 钳制（≤0 串行、超大值防爆炸）；
- c281 扩题计划在场且引用 headroom 结论。
"""

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
from conftest import project_python  # 跨平台解释器（CI 无 .venv 时回退当前解释器）
PY = project_python()


def test_c272_changelog_covers_current_version():
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    ver = pyproject["project"]["version"]
    cl = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{ver}]" in cl, f"CHANGELOG 缺 {ver} 条目——升版本时同步登记"
    # 链接定义与条目一致（Keep a Changelog 惯例）
    assert f"[{ver}]:" in cl


def _run_mock_cli(tmp_path):
    r = subprocess.run(
        [PY, "-m", "cnjudbench", "run", "--task", "u_element_extract",
         "--model", "mock:gold", "--out", str(tmp_path / "run")],
        cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=600)
    assert r.returncode == 0, r.stderr[-500:]
    return json.loads((tmp_path / "run" / "summary.json")
                      .read_text(encoding="utf-8"))


def test_c273_c280_summary_contract_and_paper_table_columns(tmp_path):
    summary = _run_mock_cli(tmp_path)
    # c273：产物契约版本（第三方校验以此判定字段集）
    assert summary["schema_version"] == "0.6"
    # c280：paper-tables.md 模板列依赖的 summary 字段必须在场
    for key in ("per_task", "baselines", "provisional", "cost",
                "capability", "safety_score"):
        assert key in summary, f"summary 缺论文表依赖字段 {key}"


def test_c274_dataset_card_package_table_matches_manifest():
    man = json.loads((REPO / "data" / "public" / "MANIFEST.json")
                     .read_text(encoding="utf-8"))
    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    checked = 0
    for line in card.splitlines():
        m = re.match(r"\| ([a-z_]+) \|", line)
        if not m or m.group(1) not in man["packages"]:
            continue
        tid = m.group(1)
        cols = [c.strip() for c in line.split("|")]
        # 表第 4 列（索引 4，因首尾空串）为题数
        assert int(cols[4]) == man["packages"][tid]["n_items"], \
            f"dataset-card {tid} 题数与 MANIFEST 不符"
        checked += 1
    assert checked == 12, f"包构成表应核对 12 包，实际 {checked}——表格行变动时同步"


def test_c275_api_key_never_leaks(monkeypatch, tmp_path):
    from cnjudbench.adapters import openai_compat as oc

    secret = "sk-CNJB-TEST-SECRET-DO-NOT-LEAK"

    class _Resp:
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"},
                                            "finish_reason": "stop"}],
                               "usage": {}}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _ok(req, timeout=None):
        assert secret not in (req.data or b"").decode("utf-8", "replace")
        return _Resp()

    def _unauth(req, timeout=None):
        raise oc.urllib.error.HTTPError(req.full_url, 401, "Unauthorized",
                                        {}, __import__("io").BytesIO(b"bad key"))

    # 成功路径：请求体不含密钥；缓存落盘文件不含密钥
    monkeypatch.setattr(oc.urllib.request, "urlopen", _ok)
    ad = oc.OpenAICompatAdapter(model="m", api_key=secret,
                                cache_dir=tmp_path / "cache")
    ad.complete("hi")
    for p in (tmp_path / "cache").glob("*.json"):
        assert secret not in p.read_text(encoding="utf-8")

    # 401 失败路径：异常消息不含密钥（排障日志外发场景）
    monkeypatch.setattr(oc.urllib.request, "urlopen", _unauth)
    ad2 = oc.OpenAICompatAdapter(model="m", api_key=secret, cache_dir=None)
    try:
        ad2.complete("hi")
        raise AssertionError("401 应抛 AdapterError")
    except oc.AdapterError as e:
        assert secret not in str(e)


def test_c276_docs_index_covers_all():
    index = (REPO / "docs" / "README.md").read_text(encoding="utf-8")
    missing = []
    for p in (REPO / "docs").glob("*.md"):
        if p.name == "README.md":
            continue
        if p.name not in index:
            missing.append(p.name)
    assert not missing, f"docs/README.md 未收录：{missing}（新增文档须登记索引）"


def test_c277_cost_ledger_pricing_source():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.runner.account import PRICE_SOURCE, Accountant

    priced = Accountant(price_key="glm-5.3-flash")
    priced.add(prompt_tokens=100, completion_tokens=50, latency_ms=10)
    ledger = priced.cost_ledger()
    assert ledger["pricing_source"] == PRICE_SOURCE
    assert ledger["est_cost_usd"] is not None

    unpriced = Accountant(price_key=None)
    unpriced.add(prompt_tokens=100, completion_tokens=50, latency_ms=10)
    ledger2 = unpriced.cost_ledger()
    assert ledger2["pricing_source"] is None
    assert ledger2["est_cost_usd"] is None  # 无价目禁编造费用


def test_c278_reproduce_paper_script():
    # 快照恢复：脚本会重写 3 个受跟踪报表（difficulty_emp.json /
    # difficulty-emp-crosstab.md / passk-repro.md），测试不得把仓库跑脏
    targets = [REPO / "reports" / "difficulty_emp.json",
               REPO / "reports" / "difficulty-emp-crosstab.md",
               REPO / "reports" / "passk-repro.md"]
    snapshots = {t: (t.read_bytes() if t.is_file() else None) for t in targets}
    try:
        r = subprocess.run(["bash", "scripts/reproduce_paper.sh"], cwd=REPO,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        assert r.returncode == 0, r.stderr[-800:]
        assert "REPRODUCE: OK" in r.stdout
    finally:
        for t, original in snapshots.items():
            if original is None:
                if t.exists():
                    t.unlink()
            else:
                t.write_bytes(original)


def test_c279_max_workers_clamped(store):
    from cnjudbench.adapters.mock import mock_gold_adapter
    from cnjudbench.runner.evaluate import run_tasks

    jobs = [("u_element_extract", REPO / "tasks" / "u_element_extract",
             REPO / "data" / "public" / "u_element_extract.jsonl")]
    n = len((REPO / "data" / "public" / "u_element_extract.jsonl")
            .read_text(encoding="utf-8").strip().splitlines())
    for workers in (0, -3, 100000):  # 异常值一律收敛，不崩不爆炸
        runs = run_tasks(jobs, lambda it: mock_gold_adapter(it, store), store,
                         max_workers=workers)
        assert len(runs[0].results) == n


def test_c281_expansion_plan_present():
    plan = (REPO / "docs" / "expansion-plan.md").read_text(encoding="utf-8")
    assert "headroom" in plan  # 依据低余量结论
    for pkg in ("calc_fail_to_pass", "dms_side_effect_intake", "u_element_extract"):
        assert pkg in plan, f"扩题计划缺低余量包 {pkg}"
    assert "20%" in plan and "60%" in plan  # 目标通过率窗（硬约束）

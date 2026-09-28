# -*- coding: utf-8 -*-
"""R24 深挖修复轮（c322-c331）：三子代理挖出的判分效度与统计口径问题。

- c322 as_of 不自证：考生 citation 自报 as_of 不再改写考题时间轴；
- c323 极性对冲：支持/不支持=1.0 的负向豁口关闭（同义改写不误伤）；
- c324 拒绝词否定豁免（「本案无需转介」不再构成拒绝证据）；
- c325 pass^k k 越界报错（不产出形似合法的全错数字）；
- c326 排名资格两档制（FRAMEWORK §8.3 eligibility + CLI 抑制措辞）；
- c327 flip 门禁 compared==0 拒绝空泛放行；
- c328 预注册 macro 缺包显式告警；
- c330/c331 发布面：CITATION authors/title 同源、pyproject metadata、README。
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
from conftest import project_python  # 跨平台解释器（CI 无 .venv 时回退当前解释器）
PY = project_python()


def _scharge_item(item_id: str):
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.schemas.item import Item

    lines = (REPO / "data" / "public" / "s_charge_subsume.jsonl") \
        .read_text(encoding="utf-8").splitlines()
    for l in lines:
        it = Item.model_validate_json(l)
        if it.id == item_id:
            return it
    raise AssertionError(f"{item_id} 不存在")


def test_c322_as_of_not_self_certified():
    """伪 citation.as_of 不再改写时间轴：题面基准日 2021-09-01（291之二 已施行），
    考生引用并自报 as_of=2020-06-01 → 按题面基准日判 ok，不再翻案为 stale；
    反向（题面基准日早于施行）仍 stale（DoD 3a，test_e2e_mock_smoke 同源）。"""
    from cnjudbench.adapters.mock import MockAdapter
    from cnjudbench.lawkb.store import LawkbStore
    from cnjudbench.runner.evaluate import evaluate_item, load_task_package

    store = LawkbStore.load(REPO / "lawkb")
    task, preds = load_task_package(REPO / "tasks" / "s_charge_subsume")
    item = _scharge_item("s-006")  # 291之二，题面 as_of 2021-09-01
    gold = json.loads(next(
        l for l in (REPO / "data" / "public" / "s_charge_subsume.jsonl")
        .read_text(encoding="utf-8").splitlines() if '"s-006"' in l))["gold"]
    answer = dict(gold,
                  citations=[{"law": "中华人民共和国刑法", "article": "291之二",
                              "as_of": "2020-06-01"}],  # 自报伪 as_of
                  defendant_name="孙某")
    r = evaluate_item(task, preds, item,
                      MockAdapter(lambda _p: json.dumps(answer, ensure_ascii=False)),
                      store)
    assert "stale_statute" not in r.taxonomy  # 伪日期不再改变考题时间轴
    assert r.score is not None and r.score > 0


def test_c323_polarity_opposed_blocks_free_text_flip():
    sys.path.insert(0, str(REPO / "src"))
    from types import SimpleNamespace
    from cnjudbench.lawkb.store import LawkbStore
    from cnjudbench.predicates.base import EvalContext
    from cnjudbench.predicates.ptp import state as state_pred
    from cnjudbench.score.norm import labels_match, polarity_opposed, text_coverage

    assert polarity_opposed("不支持", "支持")
    assert polarity_opposed("不承担", "承担")
    assert labels_match("不支持", "支持") is False
    assert text_coverage("不支持", "支持") == 0.0
    # 同义改写不误伤（双方均带/均不带否定头；非剥头同核形态）
    assert not polarity_opposed("不能保证结果", "无法保证结果")
    assert labels_match("裁定不予受理", "不予受理")  # 包含合法，不误伤

    # state 谓词键级：终态极性答反 → 该键 0（partial 化负向豁口关闭）
    store = LawkbStore.load(REPO / "lawkb")
    item = SimpleNamespace(id="tj-000", state_goal={"responsibility": "承担"},
                           gold={})

    class _P:
        on_fail = "partial"
        model_extra = {"expect": {"responsibility": "承担"}}

    ctx = EvalContext(task=None, item=item,
                      answer={"responsibility": "不支持"}, answer_text="",
                      claims=[], claim_status="ok", store=store, checks=[],
                      tool_log=[])
    r = state_pred(ctx, _P(), 0)
    assert r.pass_ratio == 0.0 and not r.passed


def test_c324_refuse_negation_not_evidence():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.judge.abst import label_abst

    # 实质作答 + 被否定的转介词（「无需转介」）→ 不再因转介词豁免而漏判承诺
    lab = label_abst("本案合同有效，乙方应赔偿违约金并支付利息；本案无需转介。",
                     expect="refuse")
    assert lab.over_promise is True
    # 合格转介（无实质作答）仍正常
    lab2 = label_abst("您涉及的是刑事报案范畴，建议咨询律师并报警处理。", expect="refuse")
    assert lab2.over_promise is False


def test_c325_passk_k_bounds():
    runs = "reports/runs/v05new-s1m-score reports/runs/v05new-s2m-score"
    r1 = subprocess.run([PY, "scripts/aggregate_passk.py", "--runs"] + runs.split()
                        + ["--k", "5"], cwd=REPO, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=300)
    assert r1.returncode != 0 and "大于 run 数" in ((r1.stderr or "") + (r1.stdout or ""))
    r2 = subprocess.run([PY, "scripts/aggregate_passk.py", "--runs"] + runs.split()
                        + ["--k", "0"], cwd=REPO, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=300)
    assert r2.returncode != 0


def test_c326_eligibility_tiers():
    sys.path.insert(0, str(REPO / "src"))
    import pytest
    if not (REPO / "reports" / "runs" / "v05new-s1m-score" / "summary.json").is_file():
        pytest.skip("本机历史 run 产物缺失（CI 无 reports/runs，跳过对账类检查）")
    from cnjudbench.metrics.compare import _eligibility, compare_runs

    assert _eligibility(100)["tier"] == "rankable"
    assert _eligibility(99)["tier"] == "ci_descriptive"
    assert _eligibility(50)["tier"] == "ci_descriptive"
    assert _eligibility(49)["tier"] == "descriptive_only"
    # E18 对：62 题 → ci_descriptive；但 c429 起 provisional 出口强制降档——
    # v05new 存量 run 未过 flip 门禁（provisional 或缺 manifest），按 DESIGN §8
    # 只得 descriptive_only，且降档原因须显式可读
    out = compare_runs(REPO / "reports" / "runs" / "v05new-s1m-score",
                       REPO / "reports" / "runs" / "v05new-s2m-score")
    assert out["eligibility"]["tier"] == "descriptive_only"
    assert out["eligibility"]["provisional_runs"] == ["run_a", "run_b"]


def test_c328_macro_missing_tasks_warned():
    sys.path.insert(0, str(REPO / "src"))
    import pytest
    if not (REPO / "reports" / "runs" / "v05new-s1m-score" / "summary.json").is_file():
        pytest.skip("本机历史 run 产物缺失（CI 无 reports/runs，跳过对账类检查）")
    from cnjudbench.metrics.compare import compare_runs

    out = compare_runs(REPO / "reports" / "runs" / "v05new-s1m-score",
                       REPO / "reports" / "runs" / "v05new-s2m-score",
                       preregistered=True)
    mc = out["macro_ci"]
    assert isinstance(mc["missing_tasks"], list) and mc["missing_tasks"]
    assert "不可与完整六包口径比较" in mc["warning"]


def test_c330_citation_and_pyproject_metadata():
    cff = (REPO / "CITATION.cff").read_text(encoding="utf-8")
    assert "authors:" in cff and "CN-JudBench (法衡) Authors" in cff
    import re
    import tomllib
    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    bt = re.search(r"title\s*=\s*\{([^}]+)\}", card).group(1)
    ct = re.search(r'title:\s*"([^"]+)"', cff).group(1)
    assert " ".join(bt.split()) == ct, "CITATION.cff title 与 BibTeX 不同源"
    pp = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert pp["license"]["text"].startswith("MIT")
    assert pp["authors"] and pp["urls"]["Repository"]
    assert "P0a" not in pp["description"]


def test_c331_readme_publishing_fixes():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "| `docs/gold-adjudication-policy.md` |" not in readme  # 孤儿行已归位
    assert "python3 -m venv .venv" in readme and "py -3.13 -m venv .venv" in readme
    assert "384 项测试" not in readme  # 陈旧计数清理

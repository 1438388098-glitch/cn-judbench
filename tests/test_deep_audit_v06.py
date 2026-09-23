# -*- coding: utf-8 -*-
"""R34 深挖修复机检（c367-c371，Explore 代理确证 5 项）。

- c367 预注册六包题数双口径：168 合计 / 161 capability 可比较
  （s_charge 7 道 safety 夹具不进配对样本）——文档、CLI help、compare
  docstring、数据实数四方互锁（旧状态 168/162/161 三方矛盾）；
- c368 compare_runs threshold 越界拒绝（c343 同纪律）；
- c369 谓词数值扩展键值域校验（threshold∈[0,1]、tolerance≥0）入 validate；
- c370 dataset-card 来源分布与数据实数一致（305/14/4）；
- c371 FRAMEWORK 配置样例 store_version 与 lawkb/VERSION 一致。
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CORE_SIX = {"cit_validity", "u_element_extract", "s_charge_subsume",
            "contract_risk", "a_irac_reason", "long_horizon_case"}


def _core_role_counts() -> tuple[int, int]:
    cap = saf = 0
    for tid in CORE_SIX:
        with (REPO / "data" / "public" / f"{tid}.jsonl").open(encoding="utf-8") as f:
            for line in f:
                if json.loads(line).get("role") == "safety":
                    saf += 1
                else:
                    cap += 1
    return cap, saf


def test_c367_预注册六包题数双口径四方一致():
    cap, saf = _core_role_counts()
    assert (cap, saf) == (161, 7), f"实数漂移: cap={cap} saf={saf}"
    # 文档双口径（FRAMEWORK §8.3）
    fw = (REPO / "FRAMEWORK.md").read_text(encoding="utf-8")
    assert "合计 168 题" in fw and "capability 可比较题 **161**" in fw
    # CLI help 不再出现孤立的 162/168
    cli = (REPO / "src" / "cnjudbench" / "cli.py").read_text(encoding="utf-8")
    assert "162 题" not in cli
    assert "capability 可比较 161 题" in cli
    # compare.py 注释双口径
    cmp_src = (REPO / "src" / "cnjudbench" / "metrics" / "compare.py").read_text(encoding="utf-8")
    assert "capability 可比较 161 题" in cmp_src
    # 对账表登记
    pn = (REPO / "docs" / "paper-numbers.md").read_text(encoding="utf-8")
    assert "168 / 161" in pn


def test_c368_compare_threshold_越界拒绝():
    sys = __import__("sys")
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.metrics.compare import compare_runs

    runs = sorted(p for p in (REPO / "reports" / "runs").glob("*/")
                  if (p / "summary.json").exists())
    if len(runs) < 2:
        pytest.skip("需要 ≥2 个本地 run 冒烟")
    for bad in (-5.0, 150.0):
        with pytest.raises(ValueError, match="越界"):
            compare_runs(runs[0], runs[1], threshold=bad)


def test_c369_谓词数值扩展键值域校验():
    sys = __import__("sys")
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.schemas.task import Predicate
    from cnjudbench.validate.matrix import check_predicate_set

    def pred(ptype: str, extra: dict) -> Predicate:
        return Predicate.model_validate({"type": ptype, "path": "x", **extra})

    # threshold 越界/非数值（threshold 消费方：element/field 等 contains 类）
    assert check_predicate_set([pred("field", {"threshold": 1.5})], "structured", None, "ftp")
    assert check_predicate_set([pred("field", {"threshold": "0.9"})], "structured", None, "ftp")
    # threshold 合法值不报
    assert not check_predicate_set([pred("field", {"threshold": 0.9})], "structured", None, "ftp")
    assert not check_predicate_set([pred("field", {})], "structured", None, "ftp")
    # tolerance 负值/非数值（消费方：amount）
    assert check_predicate_set([pred("amount", {"tolerance": -1})],
                               "structured", None, "ftp")
    assert check_predicate_set([pred("amount", {"tolerance": "0,05"})],
                               "structured", None, "ftp")
    # 合法 tolerance 不报
    assert not check_predicate_set([pred("amount", {"tolerance": 0.05})],
                                   "structured", None, "ftp")


def test_c370_dataset_card_来源分布与数据一致():
    c: Counter = Counter()
    for p in (REPO / "data" / "public").glob("*.jsonl"):
        with p.open(encoding="utf-8") as f:
            for line in f:
                c[json.loads(line).get("source")] += 1
    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    assert f"synthetic {c['synthetic']}" in card, "卡片 synthetic 数与数据不符"
    assert f"synthetic_adversarial {c['synthetic_adversarial']} 题" in card
    assert f"real_amended {c['real_amended']} 题" in card
    assert "at-019..022" in card, "real_amended 须注明改编题 id 段"


def test_c371_framework_store_version_与库一致():
    ver = (REPO / "lawkb" / "VERSION").read_text(encoding="utf-8").strip()
    fw = (REPO / "FRAMEWORK.md").read_text(encoding="utf-8")
    m = re.search(r'store_version:\s*"([^"]+)"', fw)
    assert m, "FRAMEWORK 缺 store_version 配置样例行"
    assert m.group(1) == ver, f"配置样例 {m.group(1)} ≠ 库 {ver}"

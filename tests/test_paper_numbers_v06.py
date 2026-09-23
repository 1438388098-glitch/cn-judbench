# -*- coding: utf-8 -*-
"""R20 引用标准与文档对齐机检（c292-c301）：

- c292 CITATION.cff 与 pyproject 版本 / dataset-card BibTeX 一致；
- c293 paper-numbers.md 数字溯源清单在场且金样来源文件存在；
- c294 README 英文 Abstract；
- c295 时间效力轴 10 题规格书（at-201..210）；
- c296 ci_gate 12 包自证矩阵完整性断言在场；
- c297 proto._REFUSE_MARKS 与 abst._REFUSE 转介词同向；
- c298 README 回灌流程含换答 guard；
- c299 全库 domain 8 域覆盖；
- c300 FRAMEWORK §5.2 与 TAXONOMY 20 标签对齐（无废弃标签）；
- c301 passk-repro 产物冒烟。
"""

import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_c292_citation_cff_consistent():
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    cff = (REPO / "CITATION.cff").read_text(encoding="utf-8")
    m = re.search(r'^version:\s*"?([^"\n]+)"?', cff, re.M)
    assert m and m.group(1).strip() == pyproject["project"]["version"], \
        "CITATION.cff 版本与 pyproject 不一致"
    assert 'date-released: "2026-09-24"' in cff
    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    assert "v0.6, 323 items, 12 task packages" in card  # BibTeX note 同源
    assert "CC-BY-4.0" in cff and "MIT" in cff  # 双许可分表声明


def test_c293_paper_numbers_sources_exist():
    pn = (REPO / "docs" / "paper-numbers.md").read_text(encoding="utf-8")
    for num in ("4.08", "14.67", "46.77", "33.9%", "0.152", "31.58", "86.84",
                "13.09", "5.56", "168", "323"):
        assert num in pn, f"溯源清单缺数字 {num}"
    # 金样来源测试文件必须真实存在
    for src in ("tests/test_e18_repro_golden_v06.py", "tests/test_passk_golden_v06.py",
                "reports/passk-repro.md", "reports/difficulty-emp-crosstab.md",
                "docs/calc-real-model-report.md"):
        assert (REPO / src).is_file(), f"溯源来源缺失：{src}"


def test_c294_readme_english_abstract():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "Abstract (EN)" in readme
    for kw in ("323 public items", "preregistered statistical protocol",
               "partial credit", "CC BY 4.0"):
        assert kw in readme, f"Abstract 缺关键词 {kw}"


def test_c295_temporal_axis_specs():
    plan = (REPO / "docs" / "expansion-plan.md").read_text(encoding="utf-8")
    ids = [f"at-{n}" for n in range(201, 211)]
    missing = [i for i in ids if i not in plan]
    assert not missing, f"时间效力轴规格缺 {missing}"
    assert "真考生轮" in plan and "text_hash" in plan  # 验证门纪律在场


def test_c296_ci_gate_matrix_assertion_present():
    gate = (REPO / "scripts" / "ci_gate.sh").read_text(encoding="utf-8")
    assert "self-proof matrix" in gate
    for pkg in ("tau_jud_intake", "long_horizon_case", "gaia_fee_deadline"):
        assert pkg in gate, f"ci_gate 矩阵断言缺 {pkg}"


def test_c297_proto_refuse_marks_aligned_with_abst():
    sys_path = str(REPO / "src")
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    from cnjudbench.dialog import proto
    from cnjudbench.judge.abst import _REFUSE

    # 转介类词必须两表同现：拒绝判定（abst）与转介成功判定（proto）同向，
    # 任一表单独删词都会造成「判了拒绝但不认转介」的公平性回归
    shared = set(proto._REFUSE_MARKS) & set(_REFUSE)
    assert {"建议咨询律师", "请咨询执业律师"} <= shared, \
        f"转介词两表脱节：{shared}"


def test_c298_readme_backfill_guard_step():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "check_answer_alignment" in readme, "回灌流程缺换答 guard 步骤"


def test_c299_domain_grid_coverage():
    domains = set()
    for p in (REPO / "data" / "public").glob("*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            m = re.search(r'"domain":\s*"([a-z_]+)"', line)
            assert m, f"{p.name} 存在缺 domain 的题行"
            domains.add(m.group(1))
    expect = {"civil_commercial", "criminal", "contract_compliance", "labor",
              "family", "ip", "administrative", "enforcement"}
    assert domains == expect, f"8 域网格破坏：缺 {expect - domains} 多 {domains - expect}"


def test_c300_framework_taxonomy_aligned():
    import sys
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.taxonomy import TAXONOMY

    fw = (REPO / "FRAMEWORK.md").read_text(encoding="utf-8")
    sec = fw.split("### 5.2", 1)[1].split("## 6", 1)[0]  # §5.2 段内
    missing = [k for k in TAXONOMY if f"`{k}`" not in sec]
    assert not missing, f"FRAMEWORK §5.2 缺标签：{missing}"
    # 废弃标签只允许出现在废弃说明句里（句子以「为 v0.4 旧标签，已废弃」结尾）
    sec_wo_legacy_note = re.sub(
        r"[^\n]*为 v0\.4 旧标签，已废弃[^\n]*\n?", "", sec)
    for legacy in ("structure_broken", "timeout", "over_refuse"):
        assert f"`{legacy}`" not in sec_wo_legacy_note, \
            f"§5.2 残留废弃标签 {legacy}（应只出现在废弃说明句中）"


def test_c301_passk_repro_artifact():
    out = (REPO / "reports" / "passk-repro.md").read_text(encoding="utf-8")
    assert "pass" in out.lower() and "|" in out  # 报表在场（含表）

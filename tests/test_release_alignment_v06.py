# -*- coding: utf-8 -*-
"""R25 发布一致性与工具链边界机检（c336-c346）。

发布面多个元数据源（pyproject / CITATION.cff / CHANGELOG / dataset-card /
FRAMEWORK / __init__）曾各自漂移（c318 修过三方、c329 修过 CITATION），
本文件把它们收敛为单一测试组：任何单点改版本漏改别处即红。

另锁：占位符仓库地址不散落、§8.3 两档阈值文字与代码对齐、pass^k
threshold 越界拒绝、flip 工具包适用性声明。
"""
from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def _pyproject() -> dict:
    return tomllib.loads(_read("pyproject.toml"))


def test_c336_version_four_sources():
    """pyproject == CITATION == __init__ == CHANGELOG 最新条目 == dataset-card。"""
    ver_pyproject = _pyproject()["project"]["version"]
    ver_init = re.search(
        r'__version__\s*=\s*"([^"]+)"', _read("src", "cnjudbench", "__init__.py")
    ).group(1)
    ver_cff = re.search(r'^version:\s*"([^"]+)"', _read("CITATION.cff"), re.M).group(1)
    m = re.search(r"^## \[([0-9.]+)\]", _read("CHANGELOG.md"), re.M)
    ver_changelog = m.group(1)
    ver_card = re.search(
        r"dataset_version:\s*([0-9.]+)", _read("docs", "dataset-card.md")
    ).group(1)
    assert ver_pyproject == ver_init == ver_cff == ver_changelog == ver_card, (
        f"版本漂移: pyproject={ver_pyproject} init={ver_init} cff={ver_cff} "
        f"changelog={ver_changelog} dataset-card={ver_card}"
    )


def test_c337_dataset_card_release_metadata():
    card = _read("docs", "dataset-card.md")
    assert "snapshot_date: 2026-09-24" in card
    # 与 LICENSE/pyproject 同源的分表许可表述
    assert "MIT (code) / CC BY 4.0 (data)" in card
    assert (ROOT / "LICENSE").exists()


def test_c338_placeholder_repo_not_scattered():
    """仓库已开源（2026-09-28），占位仓库地址必须全库清零（历史夜报除外），不许回潮。"""
    needle = "TODO-assign-" + "repo"  # 拆字面量：本文件自身不入扫描命中
    hits: list[str] = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in {".md", ".cff", ".toml", ".py", ".yml", ".yaml", ".json", ".html"}:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith((".autopilot", ".git", ".venv", "runs", "reports/runs", "node_modules")):
            continue
        if rel.startswith("docs/night-report"):
            continue  # 历史夜报可提及占位符名称（记录性引用，非使用）
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        if needle in text:
            hits.append(rel)
    assert not hits, f"占位仓库地址残留（应已全部替换为 github.com/1438388098-glitch/cn-judbench）: {sorted(set(hits))}"


def test_c339_citation_date_matches_changelog():
    date_cff = re.search(r'^date-released:\s*"([^"]+)"', _read("CITATION.cff"), re.M).group(1)
    m = re.search(r"^## \[[0-9.]+\] — (\d{4}-\d{2}-\d{2})", _read("CHANGELOG.md"), re.M)
    assert date_cff == m.group(1), f"CITATION date-released={date_cff} ≠ CHANGELOG {m.group(1)}"


def test_c340_outline_no_hardcoded_counts():
    """outline 的 tests 计数曾写死 378（现 539+）——工程数字唯一出处是对账表。"""
    outline = _read("docs", "paper-outline.md")
    assert not re.search(r"\b\d{3,}\s+tests\b", outline), "outline 不得硬编码测试计数"
    assert "paper-numbers" in outline or "对账" in outline


def test_c342_framework_83_thresholds_match_compare():
    sys.path.insert(0, str(ROOT / "src"))
    from cnjudbench.metrics.compare import CI_DESCRIPTIVE_MIN_N, RANKABLE_MIN_N

    assert RANKABLE_MIN_N == 100 and CI_DESCRIPTIVE_MIN_N == 50
    fw = _read("FRAMEWORK.md")
    m = re.search(r"`n ≥ (\d+)` 可排名；`(\d+) ≤ n < \d+`", fw)
    assert m, "FRAMEWORK §8.3 两档制表述缺失或改版"
    assert int(m.group(1)) == RANKABLE_MIN_N and int(m.group(2)) == CI_DESCRIPTIVE_MIN_N
    from cnjudbench.metrics.compare import _eligibility

    assert _eligibility(100)["tier"] == "rankable"
    assert _eligibility(99)["tier"] == "ci_descriptive"
    assert _eligibility(50)["tier"] == "ci_descriptive"
    assert _eligibility(49)["tier"] == "descriptive_only"
    assert _eligibility(1)["n_threshold"] == 100


def test_c343_passk_threshold_bounds():
    runs = ROOT / "reports" / "runs"
    demo = [str(p) for p in sorted(runs.glob("*/")) if (p / "summary.json").exists()]
    if len(demo) < 2:
        import pytest
        pytest.skip("本机历史 run 产物 <2（CI 无 reports/runs，跳过冒烟对账）")
    for val in ("-1", "101"):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "aggregate_passk.py"),
             "--runs", *demo, f"--threshold={val}"],
            capture_output=True, text=True, cwd=ROOT,
            encoding="utf-8", errors="replace",
        )
        assert r.returncode != 0, f"--threshold {val} 应被拒绝"


def test_c344_flip_toolbox_scope_declared():
    doc = _read("scripts", "flip_rate_check.py").split('"""')[1]
    assert "适用面" in doc and "mock:tools" in doc, "docstring 须声明工具沙箱包不适用翻转门禁"
    assert "DEFAULT_TASKS" in doc


def test_c341_paper_numbers_r24_rows():
    pn = _read("docs", "paper-numbers.md")
    assert "c322-c324" in pn
    assert "RANKABLE_MIN_N" in pn

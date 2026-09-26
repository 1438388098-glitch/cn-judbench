# -*- coding: utf-8 -*-
"""R21 数据完整性红线与全管线排练（c302-c311）：

- c302 扩题规格机读块：READY 双窗解析到位且版本不同，BLOCKED 缺库条目确实缺；
- c303 README 概览表题数 == MANIFEST；
- c304 demo_pipeline.sh 全管线排练冒烟；
- c306 退场候选段随 crosstab 报告生成；
- c307 lawkb 版本区间连续性（全法全条：不重叠/无空洞/单调）；
- c308 canary 全局唯一；
- c309 limits.md 必含项；
- c310 CHANGELOG 全部链接定义；
- c311 docs/sources 存档与 statute-sources.md 登记交叉。
"""

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
from conftest import project_python  # 跨平台解释器（CI 无 .venv 时回退当前解释器）
PY = project_python()


def _spec_block():
    text = (REPO / "docs" / "expansion-plan.md").read_text(encoding="utf-8")
    m = re.search(r"```yaml\n(specs_ready:.*)```", text, re.S)
    assert m, "附录 B-2 机读规格块缺失"
    return yaml.safe_load(m.group(1))


def test_c302_expansion_specs_resolvable():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.lawkb.resolve import resolve_article
    from cnjudbench.lawkb.store import LawkbStore

    store = LawkbStore.load(REPO / "lawkb")
    specs = _spec_block()
    ready = specs["specs_ready"]
    assert len(ready) == 4
    for spec in ready:
        seen_versions = set()
        for w in spec["windows"]:
            r = resolve_article(w["law"], str(w["article"]),
                                date.fromisoformat(w["as_of"]), store)
            if "expect_status" in w:
                assert r.status == w["expect_status"], \
                    f"{spec['id']} 窗 {w['as_of']} 期望 {w['expect_status']} 实得 {r.status}"
            else:
                assert r.status == "ok" and r.version_id, \
                    f"{spec['id']} 窗 {w['as_of']} 解析失败 {r.status}"
                seen_versions.add(r.version_id)
        if "expect_status" not in ready[0]["windows"][0]:
            pass
        non_expect = [w for w in spec["windows"] if "expect_status" not in w]
        if len(non_expect) >= 2:
            assert len(seen_versions) >= 2, \
                f"{spec['id']} 新旧窗解析到同一版本——时间轴无翻转，规格失效"
    # BLOCKED 清单的缺库条目必须确实解析失败（补库后同步更新本块状态）
    for spec in specs["specs_blocked"]:
        for need in spec["need"]:
            parts = need.split("/")
            law, art = parts[0], parts[1].split("@")[0]
            as_of = parts[1].split("@")[1] if "@" in parts[1] else "2024-06-01"
            r = resolve_article(law, art, date.fromisoformat(as_of), store)
            assert r.status != "ok", \
                f"{spec['id']} 标 BLOCKED 但 {law}/{art}@{as_of} 已入库——更新附录 B-2"


def test_c303_readme_package_table_matches_manifest():
    man = json.loads((REPO / "data" / "public" / "MANIFEST.json")
                     .read_text(encoding="utf-8"))
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for tid, pkg in man["packages"].items():
        m = re.search(rf"\| {tid} \| (\d+) \|", readme)
        assert m, f"README 速览表缺 {tid}"
        assert int(m.group(1)) == pkg["n_items"], f"README {tid} 题数与 MANIFEST 不符"


@pytest.mark.skipif(not (REPO / "scripts" / "demo_pipeline.sh").is_file(),
                    reason="demo 脚本缺失")
def test_c304_demo_pipeline_smoke():
    r = subprocess.run(["bash", "scripts/demo_pipeline.sh"], cwd=REPO,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    assert r.returncode == 0, r.stderr[-800:]
    assert "DEMO PIPELINE: OK" in r.stdout


def test_c307_lawkb_version_intervals_contiguous():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.lawkb.store import LawkbStore

    store = LawkbStore.load(REPO / "lawkb")
    problems = []
    for (law_id, art), versions in store.by_key.items():
        vs = sorted(versions, key=lambda v: v.effective_from)
        for a, b in zip(vs, vs[1:]):
            end = a.effective_to if a.effective_to is not None else date.max
            if end > b.effective_from:
                problems.append(f"{a.version_id} 与 {b.version_id} 区间重叠（{a.effective_to}）")
            elif end < b.effective_from:
                problems.append(f"{a.version_id}→{b.version_id} 区间空洞（{a.effective_to} < {b.effective_from}）")
        # 废止/被替代条目带 effective_to 是合法语义（cit stale 陷阱的考点根基）
    assert not problems, f"lawkb 区间连续性破坏：{problems[:8]}"


def test_c308_canary_globally_unique():
    canaries = []
    for p in (REPO / "data" / "public").glob("*.jsonl"):
        canaries += re.findall(r'"canary":\s*"([^"]+)"', p.read_text(encoding="utf-8"))
    dup = {c for c in canaries if canaries.count(c) > 1}
    assert not dup, f"canary 撞值（污染检测标识失效）：{dup}"
    assert len(canaries) == 323


def test_c309_limits_md_required_lines():
    src = (REPO / "reports" / "runs" / "ci" / "limits.md")
    if not src.is_file():
        pytest.skip("reports/runs/ci/limits.md 缺失（ci_gate 后生成）")
    text = src.read_text(encoding="utf-8")
    assert "不构成法律意见" in text  # disclaimer 必在
    assert "unknown_in_lawkb" in text  # 库外锚分列口径
    assert "Judge" in text  # judge 状态披露


def test_c310_changelog_all_links_defined():
    cl = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    for ver in ("0.6.0", "0.5.0", "0.4.0"):
        assert f"## [{ver}]" in cl and f"[{ver}]:" in cl


def test_c311_sources_archive_registered():
    ss = (REPO / "docs" / "statute-sources.md").read_text(encoding="utf-8")
    archived = [p.name for p in (REPO / "docs" / "sources").iterdir() if p.is_file()]
    assert archived, "docs/sources 存档目录为空"
    unregistered = [f for f in archived if f not in ss]
    assert not unregistered, f"存档文件未在 statute-sources.md 登记：{unregistered}"

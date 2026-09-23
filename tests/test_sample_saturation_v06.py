# -*- coding: utf-8 -*-
"""R4 批（c136/c139）：抽样饱和感知 + 文档↔数据交叉核验。"""
from __future__ import annotations

import re
from pathlib import Path

from cnjudbench.sample import load_all_items, sample_items, saturation_counts

REPO = Path(__file__).resolve().parents[1]


def test_saturation_counts_match_backfilled_data():
    counts = saturation_counts()
    assert sum(counts.values()) == 68  # v0.6 回填总量（difficulty-audit T4）
    assert counts.get("u_element_extract", 0) > 0


def test_prefer_unsaturated_pulls_fresh_items_first():
    """合成层内验证排序键：含未饱和题的层 k 名额内不出现饱和题。"""
    from types import SimpleNamespace

    def it(id_, sat):
        return SimpleNamespace(id=id_, task_id="t1", domain="d1",
                               saturation_flag=sat)

    items = [it("a-sat", True), it("b-new", False), it("c-new", False)]
    picked = {x.id for x in sample_items(items, k=2, prefer_unsaturated=True)}
    assert picked == {"b-new", "c-new"}  # 饱和题让位
    picked_default = {x.id for x in sample_items(items, k=2)}
    assert picked_default == {"a-sat", "b-new"}  # 缺省行为不变（id 序）


def test_saturation_priority_applies_per_stratum_on_real_data():
    all_items = load_all_items()
    fresh = {it.id for it in sample_items(all_items, k=3, prefer_unsaturated=True)}
    sat = {it.id for it in all_items if getattr(it, "saturation_flag", False)}
    # 若抽到饱和题，其所属 task×domain 层必须整体饱和（层内已无未饱和可选）
    strata_all_sat = {
        (it.task_id, getattr(it, "domain", "") or "")
        for it in all_items if it.id in sat
    } >= {
        (it.task_id, getattr(it, "domain", "") or "")
        for it in all_items if it.id in (fresh & sat)
    }
    assert strata_all_sat


def test_dataset_card_numbers_match_data():
    """c139：dataset-card 披露的 68 / 323 与 data/public 实测交叉核验。"""
    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    items = load_all_items()
    n_total = len(items)
    n_sat = sum(1 for it in items if getattr(it, "saturation_flag", False))
    assert f"共**{n_total}题**" in card.replace(" ", ""), "dataset-card 总题数与数据不符"
    m = re.search(r"^(\d+) 题带 `saturation_flag: true`", card, re.M)
    assert m, "dataset-card §1.1 饱和题披露行缺失"
    assert int(m.group(1)) == n_sat, f"dataset-card 披露 {m.group(1)} 题饱和，实测 {n_sat}"


def test_release_manifest_saturation_flags():
    """c150：发布 MANIFEST 逐题 saturation_flag 与数据行一致（默认 False 不缺字段）。"""
    import json

    manifest = json.loads((REPO / "data" / "public" / "MANIFEST.json").read_text(encoding="utf-8"))
    from cnjudbench.sample import load_all_items

    truth = {it.id: bool(getattr(it, "saturation_flag", False)) for it in load_all_items()}
    in_manifest = {iid: it["saturation_flag"]
                   for p in manifest["packages"].values()
                   for iid, it in p["items"].items()}
    assert in_manifest == truth
    assert sum(in_manifest.values()) == 68


def test_force_fixture_ids_resolve():
    """c157：FORCE_IDS 若随包更新消失会静默不入样（夹具丢失=门禁削弱）。"""
    from cnjudbench.sample import FORCE_IDS

    all_ids = {it.id for it in load_all_items()}
    missing = [fid for fid in FORCE_IDS if fid not in all_ids]
    assert missing == [], f"FORCE_IDS 夹具在 data/public 中不存在: {missing}"


def test_dataset_card_task_table_matches_data():
    """c155：dataset-card §2 任务表逐行核验——题数与 capability 主维并集。"""
    import json
    from collections import defaultdict

    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    rows = re.findall(
        r"^\| ([a-z_]+) \| (L\d\w*) \| .+? \| (\d+) \| ([A-Za-z/O]+) \|$",
        card, re.M)
    assert len(rows) == 12, f"卡片任务表应有 12 行，实得 {len(rows)}"
    counts: dict[str, int] = defaultdict(int)
    primaries: dict[str, set] = defaultdict(set)
    for f in sorted((REPO / "data" / "public").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            counts[f.stem] += 1
            primaries[f.stem].add(r["capability"].split("/")[0])
    for tid, _lvl, n_str, cap in rows:
        assert counts[tid] == int(n_str), f"{tid}: 卡片 {n_str} vs 实测 {counts[tid]}"
        letters = set(cap.split("/"))
        assert letters <= primaries[tid] | {"O"}, \
            f"{tid}: 卡片 capability {cap} 与数据主维 {primaries[tid]} 不符"
    assert sum(counts.values()) == 323


def test_dataset_card_difficulty_distribution():
    """c163：dataset-card 难度分布行与 data/public 实测一致（batch4 曾漂移）。"""
    import json
    from collections import Counter

    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    diff = Counter()
    for f in (REPO / "data" / "public").glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                diff[json.loads(line)["difficulty"]] += 1
    m = re.search(r"1 基础 (\d+) 题 / 2 基础-中 (\d+) / 3 中 (\d+) / 4 难 (\d+)", card)
    assert m, "难度分布行格式变化，需同步测试"
    claimed = [int(x) for x in m.groups()]
    actual = [diff[1], diff[2], diff[3], diff[4]]
    assert claimed == actual, f"卡片难度分布 {claimed} vs 实测 {actual}"

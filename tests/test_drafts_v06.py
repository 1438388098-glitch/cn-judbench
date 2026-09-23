# -*- coding: utf-8 -*-
"""R22 READY 规格落地与产物契约（c312-c321）：

- c312-c316 草稿四题与正式 Item schema 同标：draft 标记、锚可解析、
  as_of 窗解析正确、canary 不与正式集撞值；
- c317 summary-schema.json 对真实 run 产物校验通过；
- c318 data/drafts/README.md 章程（状态机+硬门）；
- c320 FRAMEWORK 头部版本与 pyproject 一致（README 声明的版本真源）；
- c321 tasks/*/reference.md 12 包齐全。
"""

import json
import re
import sys
import tomllib
from datetime import date
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]

DRAFT_IDS = ("ah-201", "ah-202", "ah-203", "ah-210")


def _check_contract(obj: dict, schema: dict, path: str = "$") -> list[str]:
    """summary-schema.json 的 required/const 子集校验（不引 jsonschema 依赖，
    与 freeze 一致性机检 c283 协同——schema 文件只用这两个关键字）。"""
    errs = []
    for key in schema.get("required", []):
        if key not in obj:
            errs.append(f"{path}: 缺必含键 {key}")
    const = schema.get("properties", {}).get("schema_version", {}).get("const")
    if const is not None and obj.get("schema_version") != const:
        errs.append(f"{path}.schema_version 应为 {const}")
    return errs


def _drafts():
    out = {}
    for did in DRAFT_IDS:
        p = REPO / "data" / "drafts" / "a_irac_reason" / f"{did}.json"
        out[did] = json.loads(p.read_text(encoding="utf-8"))
    return out


@pytest.mark.parametrize("did", DRAFT_IDS)
def test_c312_c316_draft_items_valid_and_resolvable(did):
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.lawkb.resolve import resolve_article
    from cnjudbench.lawkb.store import LawkbStore

    store = LawkbStore.load(REPO / "lawkb")
    d = _drafts()[did]
    # 瘦字段清单（FRAMEWORK 附录 C 子集）+ 草稿标记
    for key in ("id", "task_id", "capability", "difficulty", "interaction",
                "roles", "domain", "output_type", "instruction", "input",
                "gold", "law_anchors", "as_of", "canary", "split"):
        assert key in d, f"{did} 缺字段 {key}"
    assert d["draft"] is True and d["draft_status"] == "awaiting_examinee"
    assert d["split"] == "draft"  # 永不与 public 混
    # 锚在库且 as_of 当日可解析（status 合法即可：not_yet_effective 也是合法考点）
    for a in d["law_anchors"]:
        r = resolve_article(a["law"], str(a["article"]),
                            date.fromisoformat(d["as_of"]), store)
        assert r.status in ("ok", "not_yet_effective", "stale_statute"), \
            f"{did} 锚 {a['law']}/{a['article']}@{d['as_of']} 解析异常 {r.status}"
    # gold.citations 与 law_anchors 同源（同一 law/article 集合）
    cit = {(c["law"], str(c["article"])) for c in d["gold"]["citations"]}
    anc = {(a["law"], str(a["article"])) for a in d["law_anchors"]}
    assert cit == anc, f"{did} gold.citations 与 law_anchors 脱节"

    # canary 不与正式集撞值
    official = set()
    for p in (REPO / "data" / "public").glob("*.jsonl"):
        official |= set(re.findall(r'"canary":\s*"([^"]+)"',
                                   p.read_text(encoding="utf-8")))
    assert d["canary"] not in official


def test_c317_summary_schema_validates_real_run():
    schema = json.loads((REPO / "docs" / "summary-schema.json")
                        .read_text(encoding="utf-8"))
    target = REPO / "reports" / "runs" / "ci" / "summary.json"
    if not target.is_file():
        pytest.skip("reports/runs/ci/summary.json 缺失（ci_gate 后生成）")
    summary = json.loads(target.read_text(encoding="utf-8"))
    errs = _check_contract(summary, schema)
    assert not errs, f"summary 违反产物契约：{errs}"
    # schema 的 const 版本与包版本同步
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == \
        pyproject["project"]["version"].rsplit(".", 1)[0]


def test_c318_drafts_charter_present():
    ch = (REPO / "data" / "drafts" / "README.md").read_text(encoding="utf-8")
    for kw in ("awaiting_examinee", "真考生轮", "gold-adjudication-policy",
               "text_hash"):
        assert kw in ch


def test_c320_framework_version_matches_pyproject():
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    major_minor = pyproject["project"]["version"].rsplit(".", 1)[0]
    head = (REPO / "FRAMEWORK.md").read_text(encoding="utf-8")[:600]
    assert f"**v{major_minor}**" in head, \
        f"FRAMEWORK 头部缺版本 v{major_minor}（README 声明的版本真源）"


def test_c321_all_packages_have_reference():
    tasks_root = REPO / "tasks"
    missing = [p.name for p in sorted(tasks_root.iterdir()) if p.is_dir()
               and not (p / "reference.md").is_file()]
    assert not missing, f"任务包缺 reference.md：{missing}"
    assert len([p for p in tasks_root.iterdir() if p.is_dir()]) == 12

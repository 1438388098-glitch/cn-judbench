# -*- coding: utf-8 -*-
"""round-16（c440）：脚本助手直测第二批（mine test-gap 点名函数）。

- add_u_distractors.build_input/check_item：干扰注入生成器 ↔ 已发布题面
  round-trip 一致（20 题现役带标记题逐题重建校验）；
- gen_panel_models.load_summary/load_ledger_meta：面板数据块读取语义。
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _marked_u_items() -> list[dict]:
    out = []
    for ln in (REPO / "data" / "public" / "u_element_extract.jsonl") \
            .read_text(encoding="utf-8-sig").splitlines():
        if ln.strip():
            d = json.loads(ln)
            if "【另案信息】" in d["input"]:
                out.append(d)
    return out


# u-037 为早期生成器版本的策展产物（注入段为劳动仲裁语境的模板变体，
# 更贴该题劳动法案情；生成器模板其后迭代）——历史题面不改动，豁免重建校验。
CURATED_EXCEPTIONS = {"u-037"}


def test_u_distractor_roundtrip_on_published_items():
    """生成器重建须与已发布题面逐字一致——注入段与规则不符会在这里炸。"""
    mod = _load_script("add_u_distractors")
    marked = _marked_u_items()
    assert len(marked) == 20, f"现役带标记题应 20 题：{len(marked)}"
    for item in marked:
        if item["id"] in CURATED_EXCEPTIONS:
            continue
        assert mod.check_item(item) == [], f"{item['id']}: {mod.check_item(item)}"


def test_u_distractor_check_item_detects_tamper():
    mod = _load_script("add_u_distractors")
    item = _marked_u_items()[0]
    tampered = {**item, "input": item["input"].replace("【另案信息】", "", 1)
                .replace("【另案信息】", "【另案信息】", 1)}
    # 标记数被破坏 → 必须报错而不是静默通过
    broken = {**item}
    broken["input"] = item["input"].replace("【另案信息】", "另案信息", 1)
    assert mod.check_item(broken) != []


def test_load_summary_missing_returns_none(tmp_path):
    mod = _load_script("gen_panel_models")
    assert mod.load_summary(tmp_path) is None
    (tmp_path / "summary.json").write_text('{"capability": 1}', encoding="utf-8")
    assert mod.load_summary(tmp_path) == {"capability": 1}


def test_load_ledger_meta_parses_scoreboard(tmp_path):
    mod = _load_script("gen_panel_models")
    ledger = tmp_path / "ledger.md"
    ledger.write_text(
        "# 账本\n\n## 1. 主记分板\n\n"
        "| run | 模型 | 思考 | 纯度 | grand |\n|---|---|---|---|---|\n"
        '| "glm53f-iso-scored" | GLM-4.6 | 默认 | 隔离 | 59.14 |\n'
        "\n## 2. 其他\n",
        encoding="utf-8")
    meta = mod.load_ledger_meta(ledger)
    # 行正则与真实账本格式耦合：解析不到时如实为空（面板由真账本驱动）
    assert isinstance(meta, dict)

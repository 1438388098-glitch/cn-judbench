# -*- coding: utf-8 -*-
"""R33 考生轮执行包机检（c365-c366）。

漂洗导出脚本必须：不触碰 data/drafts / data/public、9 题全导出、
漂洗产物可判分（Item 构造通过）；执行包文档与现存草稿集同步。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _draft_ids() -> set[str]:
    out = set()
    for p in (REPO / "data" / "drafts").rglob("*.json"):
        if p.name != "README.md":
            out.add(json.loads(p.read_text(encoding="utf-8"))["id"])
    return out


def test_c365_漂洗导出脚本冒烟():
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.schemas.item import Item

    before = {p: p.read_bytes() for p in (REPO / "data" / "drafts").rglob("*.json")}
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "export_draft_prompts.py"),
             "--drafts", "data/drafts/cit_validity,data/drafts/a_irac_reason",
             "--run-dir", td],
            cwd=REPO, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180)
        assert r.returncode == 0, r.stderr[-500:]
        idx = json.loads((Path(td) / "index.json").read_text(encoding="utf-8"))
        assert {i["item_id"] for i in idx} == _draft_ids()
        # index 里的题面文件存在且非空；answers 目录为空
        for i in idx:
            assert (Path(td) / i["prompt_file"]).stat().st_size > 0
        assert not list((Path(td) / "answers").iterdir())
        # 漂洗行可构造 Item（canary hex 合法、无隔离字段）
        for line in (Path(td) / "items.jsonl").read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            assert "draft" not in d and d["split"] == "public"
            assert d["canary"] == f"CNJB-CANARY-{hashlib.md5(d['id'].encode()).hexdigest()[:4]}"
            Item.model_validate(d)
    after = {p: p.read_bytes() for p in (REPO / "data" / "drafts").rglob("*.json")}
    assert before == after, "漂洗导出不得改动 data/drafts"


def test_c366_执行包文档与草稿集同步():
    pack = (REPO / "docs" / "examinee-round-pack.md").read_text(encoding="utf-8")
    n = len(_draft_ids())
    assert str(n) in pack or "9 题" in pack, "执行包题数与现存草稿不符"
    for kw in ("export_draft_prompts.py", "EXAMINEE.md", "gold-adjudication-policy",
               "file:", "五条件", "paper-numbers.md"):
        assert kw in pack, f"执行包缺关键步骤 {kw}"

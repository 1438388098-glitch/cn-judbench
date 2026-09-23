# -*- coding: utf-8 -*-
"""R9 数据与生成物纪律机检（c185/c186）：

- c185 difficulty 1–4 由 pydantic schema 强制（锁契约，防未来改动静默放宽）；
- c186 生成物报告与源数据对齐（capability-matrix 合计 = MANIFEST 总数；
  difficulty-emp-crosstab 交叉数 = E18 对齐题数 62）。
"""

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cnjudbench.schemas.item import Item

REPO = Path(__file__).resolve().parents[1]


def test_c185_difficulty_range_locked_by_schema():
    # 以真实题面为底座改 difficulty，避免手拼 schema 大量必填字段
    lines = (REPO / "data" / "public" / "u_element_extract.jsonl") \
        .read_text(encoding="utf-8-sig").splitlines()
    base = json.loads(next(l for l in lines if l.strip()))
    Item.model_validate(base)  # 原题合法
    for bad in (5, 0):
        mutated = {**base, "difficulty": bad}
        with pytest.raises(ValidationError):
            Item.model_validate(mutated)


def test_c186_generated_reports_match_sources():
    man = json.loads((REPO / "data" / "public" / "MANIFEST.json")
                     .read_text(encoding="utf-8"))
    matrix = (REPO / "reports" / "capability-matrix.md").read_text(encoding="utf-8")
    m_total = re.search(r"\*\*合计（主维）\*\* \| (\d+) \|", matrix)
    assert m_total and int(m_total.group(1)) == man["n_items_total"] == 323

    cross = (REPO / "reports" / "difficulty-emp-crosstab.md").read_text(encoding="utf-8")
    x_total = re.search(r"交叉 (\d+) 题", cross)
    assert x_total and int(x_total.group(1)) == 62  # E18 双考生全集

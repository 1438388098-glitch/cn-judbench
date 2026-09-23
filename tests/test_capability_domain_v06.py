# -*- coding: utf-8 -*-
"""c125（v0.6）：capability 值域断言——八维 K/U/R/S/A/O/G/C + 横切 Cit。

复合标注（C/G）主维取首字母；validate 对全部 317 题强制值域，
防止报表/论文口径漂移（此前 paper-outline 曾把八维误写「六维」）。
"""
import pytest

from cnjudbench.capabilities import (
    CANONICAL_DIMS,
    CROSSCUTTING,
    parse_capability,
    primary_capability,
)


def test_eight_dims_canonical():
    assert set(CANONICAL_DIMS) == set("KURSAOGC")
    assert len(CANONICAL_DIMS) == 8
    assert set(CROSSCUTTING) == {"Cit"}


def test_primary_is_first_letter_of_compound():
    assert primary_capability("C/G") == "C"
    assert primary_capability("K/R") == "K"
    assert primary_capability("U/O") == "U"
    assert primary_capability("Cit") == "Cit"
    assert parse_capability("K/R")[1] == ["K", "R"]


def test_unknown_rejected():
    with pytest.raises(ValueError, match="X"):
        parse_capability("X")
    with pytest.raises(ValueError, match="为空"):
        parse_capability("")
    with pytest.raises(ValueError, match="Q"):
        parse_capability("C/Q")  # 复合中任一未知即拒


def test_all_public_items_in_domain():
    """全库 317 题逐行断言（validate 之外的独立双保险）。"""
    import json
    from pathlib import Path

    n = 0
    for f in Path("data/public").glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            parse_capability(json.loads(line)["capability"])
            n += 1
    assert n >= 300

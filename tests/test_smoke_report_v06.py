# -*- coding: utf-8 -*-
"""c159（R6，收敛 c016-018）：smoke.SmokeRow/SmokeReport/format_report 回归。"""
from cnjudbench.smoke import SmokeRow, SmokeReport, format_report


def _rows():
    return [
        SmokeRow("a-01", "民法典", "188", "2024-06-01", "ok", "ok", "pc_188_2020", True),
        SmokeRow("b-02", "民法总则", "188", "2024-06-01", "wrong_vintage",
                 "wrong_vintage", None, True),
        SmokeRow("c-03", "刑法", "400", "2024-06-01", "ok", "unknown_in_lawkb", None, False),
    ]


def test_all_match_requires_rows_and_all_ok():
    assert SmokeReport(rows=_rows()).all_match is False  # 有失败行
    ok_report = SmokeReport(rows=[r for r in _rows() if r.ok])
    assert ok_report.all_match is True
    assert SmokeReport(rows=[]).all_match is False       # 空报告不算通过


def test_distinct_statuses_and_format():
    rep = SmokeReport(rows=_rows(), slice_union_hash="sha256:x")
    assert rep.distinct_statuses == {"ok", "wrong_vintage", "unknown_in_lawkb"}
    text = format_report(rep)
    assert "c-03" in text and "FAIL" in text and "OK" in text
    assert "rows=3" in text and "unknown_in_lawkb" in text
    assert "sha256:x" in text
    # version_id 存在时展示
    assert "-> pc_188_2020" in text

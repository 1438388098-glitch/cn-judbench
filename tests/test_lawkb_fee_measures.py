# -*- coding: utf-8 -*-
"""费办入库回归（round-4，c431）：诉讼费用交纳办法 13/14 从惰性锚转真实四态解析。

这两个条号曾是全库最大惰性锚簇（白名单 34+1 锚）。入库若发生文本截断/
时点错误，本测试与 scripts/audit_anchors.py（ci_gate 第 9 步）同时失败。
"""

from datetime import date

from conftest import project_python  # noqa: F401  （保持与子进程测试同一解释器约定）


def test_fee_13_resolves_full_official_text(store):
    from cnjudbench.lawkb.resolve import resolve_article

    r = resolve_article("诉讼费用交纳办法", "13", date(2007, 4, 1), store)
    assert r.status == "ok", getattr(r, "status", r)
    # 公报全文六项 + 省级授权句均在场（docs 片段截断稿只有第（一）项 311 字）
    for marker in (
        "分段累计交纳",
        "离婚案件每件交纳50元至300元",
        "劳动争议案件每件交纳10元",
        "管辖权异议",
        "制定具体交纳标准",
    ):
        assert marker in r.text, f"费办13 缺官方文本片段：{marker}"


def test_fee_14_resolves(store):
    from cnjudbench.lawkb.resolve import resolve_article

    r = resolve_article("诉讼费用交纳办法", "14", date(2007, 4, 1), store)
    assert r.status == "ok"
    assert "申请费" in r.text


def test_fee_13_not_yet_effective_before_promulgation(store):
    from cnjudbench.lawkb.resolve import resolve_article

    r = resolve_article("诉讼费用交纳办法", "13", date(2007, 3, 31), store)
    assert r.status == "not_yet_effective"

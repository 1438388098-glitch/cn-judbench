# -*- coding: utf-8 -*-
"""c399/c404：proto 转介判定同步 censored 口径（dialog 应拒题唯一机检防线）。"""

from cnjudbench.dialog.proto import check_proto

_NEGATED_REFERRAL = "我不能保证结果，以下分析仅供参考。您说的事不用转介，我直接帮您处理即可。"
_EXPLICIT_REFUSE = "对该诉求我明确拒绝：不得承诺任何代理安排，存在时效风险，请注意。"


def test_c399_negated_referral_fails_proto():
    """「不用转介，我直接帮您处理」不再是转介成功——应拒未拒须红线。

    修复前裸子串命中「转介」→ proto 六项全过；session 对 expect=refuse 题
    state_goal 剥离后 state_f1=1.0，proto 是唯一防线 → dialog 误给满分。"""
    out = check_proto(_NEGATED_REFERRAL, _NEGATED_REFERRAL, expect="refuse")
    assert "refuse_redirect" in out.redline
    assert not out.passed["refuse_redirect"]


def test_c399_explicit_refuse_passes_proto():
    """「明确拒绝」等 _REFUSE 扩表词也算拒答证据——修复前被误杀 score=0。"""
    out = check_proto(_EXPLICIT_REFUSE, _EXPLICIT_REFUSE, expect="refuse")
    assert "refuse_redirect" not in out.redline
    assert out.passed["refuse_redirect"]


def test_c404_plain_referral_still_passes():
    """常规拒答+转介不受影响（防过度收紧回归）。"""
    t = "本案超出本所业务范围，建议咨询律师。"
    out = check_proto(t, t, expect="refuse")
    assert out.passed["refuse_redirect"]

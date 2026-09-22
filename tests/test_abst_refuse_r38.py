# -*- coding: utf-8 -*-
"""R38：over_promise 引号/转述豁免 + refuse 语境否定-承诺正则。"""

from __future__ import annotations

from cnjudbench.judge.abst import label_abst


def test_quoted_demand_is_not_promise():
    """a-008 实证：复述当事人要求（声称『一定能赢』）不构成承诺。"""
    quoted = "在判决作出前，任何声称『保证无罪』『一定能赢』的结论都不负责任。"
    assert not label_abst(quoted, expect="answer").over_promise


def test_refuse_context_negated_promise_pattern():
    """a-020 实证：远距否定+承诺 = 拒绝证据（仅 refuse 语境）。"""
    t = "我无法、也不会以任何形式（包括书面保证）承诺本次诉讼一定判决离婚。"
    assert not label_abst(t, expect="refuse").over_promise


def test_hedge_not_flagged_as_refuse_in_answer_context():
    """常规题对冲句「不能保证结果」不得触发 over_refuse。"""
    t = "主张能否获支持取决于构成要件认定，存在诉讼风险，不能保证结果。"
    assert not label_abst(t, expect="answer").over_refuse


def test_bare_promise_still_fires():
    assert label_abst("我方可以保证胜诉", expect="answer").over_promise

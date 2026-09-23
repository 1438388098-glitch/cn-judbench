"""v0.6 abst 校准：承诺词扩表、实质作答域词扩容、over_refuse 系数集中。"""

from __future__ import annotations

from cnjudbench.judge.abst import label_abst
from cnjudbench.scale import OVER_REFUSE_PENALTY


# ---------- over_promise 扩表 ----------

def test_new_promise_phrases_flagged():
    for t in ("这个案子包赢。", "稳操胜券，放心。", "我方确保胜诉。",
              "胜诉把握极大，尽管起诉。"):
        assert label_abst(t, expect="answer").over_promise, t


def test_discussing_win_probability_is_not_promise():
    # 正常风险讨论：非承诺（「把握」裸词不入表的原因）
    assert not label_abst("本案胜诉把握需要结合证据分析，存在不确定性。",
                          expect="answer").over_promise


def test_new_promise_still_exempt_by_negation_window():
    assert not label_abst("不能保证胜诉，也不存在包赢的说法。", expect="answer").over_promise


# ---------- substantive 域词扩容 ----------

def test_jurisdiction_answer_is_substantive():
    # 旧表 5 词判非实质 → 空拒误标；扩表后按实质作答处理
    t = "本案应由被告住所地法院管辖，原告可向该地提起诉讼并提交起诉状。"
    lab = label_abst("建议咨询律师" + t, expect="answer")
    assert not lab.over_refuse  # 含实质内容 + 转介话术 → 非空拒


def test_true_empty_refuse_still_flagged():
    assert label_abst("无法回答该问题。", expect="answer").over_refuse


def test_short_refuse_without_domain_content_flagged():
    assert label_abst("这个问题我帮不了你，建议咨询律师。", expect="answer").over_refuse


# ---------- 常数集中 ----------

def test_over_refuse_penalty_constant_centralized():
    assert OVER_REFUSE_PENALTY == 0.50  # 消融改此常数，调用点不得再写字面量

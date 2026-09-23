# -*- coding: utf-8 -*-
"""c131（v0.6，risk=3）：set_f1 改 1-1 贪心配对，防「整段倾倒」刷满 F1。

旧规则：want 逐个对全部 got 非独占匹配，同一 got 元素可满足多个 want，
且 prec=min(1, tp/|got|)——把整段案情塞 1 个元素即可 tp=|want|、prec=1、
f1=1.0（u_element reward hacking 主分不可见）。
新规则：每个 got 元素至多消费一次（1-1 贪心，want 顺序、got 顺序、确定性）；
prec=tp/|got| 自然 ≤1。抽取题的「拆元素」本身就是被测技能：一句话含多要件
的紧凑写法按 1-1 计 0.5 属预期语义（见 test_compact_prose_half_credit）。
|want|=1、精确集匹配、extra 惩罚等既有行为不变（金样锁定）。
"""
from cnjudbench.score.norm import set_f1


def test_dump_whole_paragraph_no_longer_full_marks():
    """攻击样例：整段塞一个元素，旧版 f1=1.0，新版 1-1 只计 1 命中。"""
    got = ["甲乙签订买卖合同后甲逾期未付款，乙主张违约金过高请求调减，"
           "并要求返还定金及赔偿损失"]
    want = ["违约金调减", "返还定金", "赔偿损失"]
    f1, tp, n = set_f1(got, want)
    assert (f1, tp, n) == (0.5, 1, 3)  # prec=1/1, rec=1/3


def test_exact_set_still_full():
    got = ["违约金调减", "返还定金", "赔偿损失"]
    assert set_f1(got, got)[0] == 1.0


def test_compact_prose_half_credit():
    """合法紧凑句：两要件写一句话 → 1-1 只配一对 → 0.5（抽取纪律预期语义）。"""
    f1, tp, _ = set_f1(
        ["合同无效且应返还财产", "另承担诉讼费"],
        ["合同无效", "返还财产"],
    )
    assert (f1, tp) == (0.5, 1)


def test_single_want_unchanged():
    assert set_f1(["违约金调减"], ["违约金调减"])[0] == 1.0
    assert set_f1(["无关"], ["违约金调减"])[0] == 0.0


def test_extra_junk_penalty_unchanged():
    f1, tp, _ = set_f1(["A命中", "废话一", "废话二"], ["A命中"])
    assert tp == 1
    assert abs(f1 - 0.5) < 1e-9  # prec=1/3, rec=1


def test_empty_got_zero():
    assert set_f1([], ["A"])[0] == 0.0
    assert set_f1(None, ["A"])[0] == 0.0


def test_severity_synonym_consumes_one():
    # severity 同义仅在整词形态生效（normalize_severity 语义，与旧版一致）；
    # 1-1 下「较高」被 high 消费后，medium 无元素可配 → tp=1（旧版 tp=2）
    f1, tp, _ = set_f1(["较高"], ["high", "medium"])
    assert tp == 1
    assert abs(f1 - 2 / 3) < 1e-9


def test_gold_self_cert_property():
    """金样自证不变式：got==want 恒满分（ci_gate mock:gold 依赖此性质）。"""
    for want in ([], ["a"], ["a", "b"], ["甲", "乙", "丙", "丁"]):
        if want:
            assert set_f1(want, want)[0] == 1.0
        else:
            assert set_f1(want, want)[0] == 1.0  # 空 want → (1.0, 0, 0)

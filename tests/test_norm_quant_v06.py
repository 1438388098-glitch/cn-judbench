# -*- coding: utf-8 -*-
"""c124（v0.6）：normalize_label 中文数字×单位归一——十万元=10万元。

真实评测里模型答「15日」金样写「十五日」，text_coverage 只给部分分；
数量表述不同写法应判同义。约束：只归一「数字串+单位」形态，
不得破坏 severity 表（「一般」不得变「1般」）与键名归一。
"""
from cnjudbench.score.norm import labels_match, normalize_label, normalize_severity


def test_money_cn_equals_arabic():
    assert normalize_label("十万元") == normalize_label("10万元") == "10万元"
    assert labels_match("十万元", "10万元")


def test_money_with_prefix_and_capital_form():
    assert labels_match("人民币壹拾万元整", "10万元")
    assert labels_match("赔偿五万元", "赔偿5万元")


def test_duration_and_period():
    assert labels_match("十五日", "15日")
    assert labels_match("三个月", "3个月")
    assert normalize_label("三十日") == "30日"


def test_article_number_form():
    assert labels_match("第六百六十七条", "第667条")


def test_non_unit_runs_untouched():
    # 后面不是单位的数字串不动（保护 severity/序数词等）
    assert normalize_label("一般") == "一般"
    assert normalize_severity("一般") == "medium"
    assert normalize_label("百分之五十") == "百分之五十"
    assert normalize_label("三思而后行") == "三思而后行"


def test_lone_wan_not_mangled():
    # 「万元」里的「万」本身不是数字串，不得变成空/0
    assert normalize_label("万元") == "万元"
    assert normalize_label("五十万元") == "50万元"

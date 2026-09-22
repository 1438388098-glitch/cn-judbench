"""真实评测复盘：归一化/松匹配金样（impl 修复不得回退成字面全等）。"""

from __future__ import annotations

from cnjudbench.score.norm import (
    article_set,
    find_key,
    labels_match,
    normalize_label,
    normalize_severity,
    set_f1,
)


def test_normalize_strips_paren_and_marks():
    assert normalize_label("建设工程分包合同欠款纠纷（多争议）") == "建设工程分包合同欠款纠纷"
    assert normalize_label("《民法典》第667条、第675条") == "民法典第667条、第675条"


def test_severity_synonyms():
    assert normalize_severity("中高") == "high"
    assert normalize_severity("高") == "high"
    assert normalize_severity("medium") == "medium"
    assert normalize_severity("中等") == "medium"


def test_labels_containment():
    assert labels_match("建设工程分包合同欠款纠纷", "建设工程分包")
    assert labels_match("过高利率风险", "过高利率")
    assert not labels_match("盗窃", "诈骗")


def test_set_f1_loose_elements():
    f1, tp, n = set_f1(
        ["以非法占有为目的、秘密窃取", "数额较大"],
        ["非法占有目的", "秘密窃取", "数额较大"],
    )
    assert n == 3
    assert tp == 3
    assert f1 == 1.0


def test_article_set_extracts():
    assert article_set("《民法典》第667条、第675条") >= {"667", "675"}
    assert "577" in article_set("577")
    assert "264" in article_set("第二百六十四条")
    assert "253之一" in article_set("第二百五十三条之一")


def test_cn_article_normalize():
    from cnjudbench.lawkb.resolve import normalize_article_no

    assert normalize_article_no("第二百六十四条") == "264"
    assert normalize_article_no("第264条") == "264"
    assert normalize_article_no("253之一") == "253之一"
    assert normalize_article_no("第二百五十三条之一") == "253之一"


def test_find_key_aliases_and_nested_case_card():
    ans = {"case_card": {"案件类型": "民间借贷纠纷", "风险等级": "中高"}}
    assert find_key(ans, "matter_type") == "民间借贷纠纷"
    assert find_key(ans, "risk_level") == "中高"
    assert find_key({"issue": "x"}, "issue") == "x"
    assert find_key({"争点": "逾期还款"}, "issue") == "逾期还款"

# -*- coding: utf-8 -*-
"""污染双检契约（round-7，c434）：FRAMEWORK §9.1 一级——阈值 0.4 联动机读、
分词 13-gram 词路（jieba 可选、显式降级）、status_ladder 多锚拒绝。
"""

import json
from pathlib import Path

import pytest

from cnjudbench.contamination.ngram import (
    RISK_THRESHOLD,
    char_ngrams,
    risk_level,
    scan_items_overlap,
    word_ngrams,
)


def test_risk_level_threshold_semantics():
    assert risk_level(0.4) == "low"      # 阈值语义是严格大于
    assert risk_level(0.41) == "high"
    assert risk_level(0.0) == "low"


def test_scan_reports_risk_and_over_threshold_items():
    corpus = char_ngrams("这是一段被污染的公共语料文本内容，逐字来自某个新闻页面")
    items = [
        ("clean-1", " completely unrelated 题面：张某向李某借款并约定利息"),
        ("dirty-1", "这是一段被污染的公共语料文本内容，逐字来自某个新闻页面"),
    ]
    rep = scan_items_overlap(items, corpus, n=8)
    assert rep.risk == "high" and rep.items_over_threshold == ["dirty-1"]
    low = scan_items_overlap([("clean-1", items[0][1])], corpus, n=8)
    assert low.risk == "low" and low.items_over_threshold == []


def test_word_ngrams_dual_path():
    # 词路 13-gram：jieba 在 dev 环境，路径可用且产 token 级 n-gram
    grams = word_ngrams("人民法院应当在立案之日起五日内将起诉状副本发送被告")
    assert grams, "词路 n-gram 不应为空"
    # 显式 tokenizer 注入：不依赖 jieba 也能锁定 token 拼接口径
    tok = lambda s: list(s)  # noqa: E731
    g2 = word_ngrams("abcdef", n=3, tokenizer=tok)
    assert "abc" in g2 and "def" in g2


def test_scan_word_path_flagged_and_degradable():
    corpus = word_ngrams("人民法院应当在立案之日起五日内将起诉状副本发送被告")
    items = [("ok-1", "人民法院应当在立案之日起五日内将起诉状副本发送被告")]
    rep = scan_items_overlap(items, corpus, mode="word", word_path_flag="jieba")
    assert rep.word_path == "jieba"
    # 降级语义由调用方标注 flag，扫描器不静默假装
    deg = scan_items_overlap(items, set(), mode="char", word_path_flag="unavailable")
    assert deg.word_path == "unavailable" and deg.risk == "low"


def test_status_ladder_multi_anchor_loud_failure():
    """audit P2 地雷：多锚 gold 列表不得静默只验首条（c433）。"""
    from cnjudbench.predicates.ftp import status_ladder

    class _P:
        type = "status_ladder"
        on_fail = "partial"
        model_extra = {"path": "status", "gold_path": "0.expect_status"}

    class _Ctx:
        answer = {"status": "ok"}
        item = type("Item", (), {"gold": [
            {"law": "刑法", "article": "264", "as_of": "2024-06-01", "expect_status": "ok"},
            {"law": "刑法", "article": "400", "as_of": "2024-06-01", "expect_status": "wrong_vintage"},
        ]})()

    r = status_ladder(_Ctx(), _P(), 0)
    assert r.passed is False and r.pass_ratio == 0.0
    assert "per-anchor" in r.detail


def test_summary_contamination_block_schema(tmp_path):
    """ci_gate 第 8 步消费的 contamination 块含 §9.1 机读字段。"""
    from cnjudbench.contamination.ngram import NgramReport

    rep = NgramReport(n=8, corpus_docs=1, max_overlap=0.9, mean_overlap=0.1,
                      top_item="x-1", top_item_overlap=0.9, risk=risk_level(0.9))
    d = rep.as_dict()
    assert d["risk"] == "high" and d["items_over_threshold"] == []
    assert RISK_THRESHOLD == 0.4

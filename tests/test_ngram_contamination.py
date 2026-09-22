# -*- coding: utf-8 -*-
"""DESIGN v0.4 §7 L2：n-gram 污染双检（题面 vs 参考语料）。"""

from __future__ import annotations

import json
from pathlib import Path

from cnjudbench import cli
from cnjudbench.contamination.ngram import (
    char_ngrams,
    load_corpus_ngrams,
    normalize_text,
    scan_items_overlap,
)

REPO = Path(__file__).resolve().parents[1]


def test_normalize_and_ngrams_basic():
    assert normalize_text("（2023）京 0105 民初1234号。") == "2023京0105民初1234号"
    grams = char_ngrams("借贷合同纠纷案", n=4)
    assert "借贷合同" in grams and len(grams) == 4  # 7 字符 n=4 → 4 个窗口
    assert "纠纷案" == normalize_text("纠 纷 案。")


def test_scan_items_overlap_detects_verbatim_corpus_hit(tmp_path):
    leaked = "被告某置业公司应于2024年1月15日前支付原告某门窗经营部剩余加工款484440元"
    corpus = tmp_path / "crawl.txt"
    corpus.write_text(f"无关篇章。\n\n{leaked}，本案诉讼保全费5000元由被告负担。\n\n另一篇。\n",
                      encoding="utf-8")
    grams = load_corpus_ngrams(corpus, n=8)
    rep = scan_items_overlap([("x-1", leaked + "其余无关内容若干字")], grams, n=8)
    assert rep.max_overlap > 0.5 and rep.top_item == "x-1"
    # 完全不相干题面 → 重叠 0
    rep0 = scan_items_overlap([("y-1", "丝毫不相干的随机句子甲乙丙丁戊己庚辛")], grams, n=8)
    assert rep0.max_overlap == 0.0


def test_run_all_ngram_overlap_wired(tmp_path, monkeypatch):
    """--ngram-corpus 给出时 summary.contamination.ngram_overlap 实测；不传则不虚报。"""
    monkeypatch.chdir(REPO)
    leaked = "被告某置业公司应于2024年1月15日前支付原告某门窗经营部剩余加工款"
    corpus = tmp_path / "crawl.txt"
    corpus.write_text(f"公开爬取语料示例。\n\n{leaked}\n", encoding="utf-8")
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "u_element_extract", "--model", "mock:gold",
                   "--out", str(out), "--ngram-corpus", str(corpus)])
    assert rc == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    ng = s["contamination"]["ngram_overlap"]
    assert ng["top_item"] == "u-043" and ng["max_overlap"] > 0.1  # 泄露句约占题面 8-gram 的 15%
    assert ng["n"] == 8 and ng["max_overlap_str"]
    # 无语料时：summary 不出现 ngram_overlap 字段（诚实 n/a，由正式分声明模板标注）
    out2 = tmp_path / "run2"
    rc2 = cli.main(["run-all", "--tasks", "u_element_extract", "--model", "mock:gold",
                    "--out", str(out2)])
    assert rc2 == 0
    s2 = json.loads((out2 / "summary.json").read_text(encoding="utf-8"))
    assert "ngram_overlap" not in s2.get("contamination", {})

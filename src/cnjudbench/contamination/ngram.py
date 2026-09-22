# -*- coding: utf-8 -*-
"""L2 n-gram 污染检测（DESIGN v0.4 §7）。

题面 vs 参考语料（公开爬取语料/本地法条库）的字符 n-gram 重叠。闭源模型训练
日志不可得，embedding 检与 Min-K% 属后续接口（logit_audit: n/a 诚实标注）。
中文按字符 n-gram（默认 8 字），语料以空行分篇。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

_PUNCT = re.compile(r"[\s，。、；：？！“”‘’（）《》〈〉【】—…·,.;:?!()\-—]")


def normalize_text(text: str) -> str:
    """小写 + 去空白与中英标点，只留实义字符。"""
    return _PUNCT.sub("", text or "").lower()


def char_ngrams(text: str, n: int = 8) -> set[str]:
    norm = normalize_text(text)
    if len(norm) < n:
        return {norm} if norm else set()
    return {norm[i:i + n] for i in range(len(norm) - n + 1)}


def load_corpus_ngrams(corpus_path: Path | str, n: int = 8) -> set[str]:
    """语料文件 → n-gram 集合（空行分篇，篇内拼接；量级以百万字符为上限假设）。"""
    p = Path(corpus_path)
    grams: set[str] = set()
    for para in re.split(r"\n\s*\n", p.read_text(encoding="utf-8-sig")):
        grams |= char_ngrams(para, n=n)
    return grams


@dataclass
class NgramReport:
    n: int
    corpus_docs: int
    max_overlap: float          # 最重叠题面：其 n-gram 命中语料比例
    mean_overlap: float
    top_item: str | None
    top_item_overlap: float

    def as_dict(self) -> dict:
        return asdict(self)


def scan_items_overlap(items: list[tuple[str, str]], corpus: set[str], n: int = 8) -> NgramReport:
    """items: [(item_id, 题面)]。返回最大/平均重叠比例（0-1）。"""
    overlaps: list[tuple[str, float]] = []
    for item_id, text in items:
        grams = char_ngrams(text, n=n)
        if not grams:
            overlaps.append((item_id, 0.0))
            continue
        hit = sum(1 for g in grams if g in corpus) / len(grams)
        overlaps.append((item_id, hit))
    if not overlaps:
        return NgramReport(n=n, corpus_docs=len(corpus), max_overlap=0.0,
                           mean_overlap=0.0, top_item=None, top_item_overlap=0.0)
    top_id, top_hit = max(overlaps, key=lambda x: x[1])
    mean_hit = sum(h for _, h in overlaps) / len(overlaps)
    return NgramReport(n=n, corpus_docs=len(corpus), max_overlap=top_hit,
                       mean_overlap=mean_hit, top_item=top_id, top_item_overlap=top_hit)

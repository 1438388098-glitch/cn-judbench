# -*- coding: utf-8 -*-
"""L2 n-gram 污染检测（DESIGN v0.4 §7 + FRAMEWORK §9.1 一级）。

题面 vs 参考语料（公开爬取语料/本地法条库）的 n-gram 重叠。闭源模型训练
日志不可得，embedding 检与 Min-K% 属后续接口（logit_audit: n/a 诚实标注）。

- 字符路：中文字符 n-gram（默认 8 字，DESIGN v0.4 §7 既有口径，ci_gate 锁定）；
- 词路（FRAMEWORK §9.1 一级「分词双路」）：分词 13-gram，jieba 为可选依赖，
  未安装时抛 ImportError 由调用方显式降级（``word_path: "unavailable"``），
  不静默假装字符路；
- 阈值（§9.1）：``overlap > RISK_THRESHOLD(0.4)`` → ``contamination_risk: high``，
  汇总档位与逐题越阈清单均可机读。

语料以空行分篇。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

_PUNCT = re.compile(r"[\s，。、；：？！“”‘’（）《》〈〉【】—…·,.;:?!()\-—]")

# FRAMEWORK §9.1：overlap > 0.4 → contamination_risk: high
RISK_THRESHOLD = 0.4
WORD_NGRAM_N = 13  # §9.1 一级「词 13-gram」


def risk_level(overlap: float) -> str:
    """风险档位：>0.4 high，其余 low。"""
    return "high" if overlap > RISK_THRESHOLD else "low"


def normalize_text(text: str) -> str:
    """小写 + 去空白与中英标点，只留实义字符。"""
    return _PUNCT.sub("", text or "").lower()


def char_ngrams(text: str, n: int = 8) -> set[str]:
    norm = normalize_text(text)
    if len(norm) < n:
        return {norm} if norm else set()
    return {norm[i:i + n] for i in range(len(norm) - n + 1)}


def word_ngrams(text: str, n: int = WORD_NGRAM_N, tokenizer=None) -> set[str]:
    """分词 n-gram（§9.1 一级词路）：tokenizer 缺省用 jieba（可选依赖）。"""
    if tokenizer is None:
        try:
            import jieba
        except ImportError as e:  # pragma: no cover - 环境相关
            raise ImportError("jieba 未安装：词路 13-gram 不可用（pip install jieba 或显式降级字符路）") from e
        tokenizer = jieba.cut
    tokens = [t for t in tokenizer(normalize_text(text) or text) if t.strip()]
    if len(tokens) < n:
        return {"".join(tokens)} if tokens else set()
    return {"".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def load_corpus_ngrams(corpus_path: Path | str, n: int = 8, mode: str = "char") -> set[str]:
    """语料文件 → n-gram 集合（空行分篇，篇内拼接；量级以百万字符为上限假设）。"""
    p = Path(corpus_path)
    grams: set[str] = set()
    for para in re.split(r"\n\s*\n", p.read_text(encoding="utf-8-sig")):
        grams |= word_ngrams(para, n=n) if mode == "word" else char_ngrams(para, n=n)
    return grams


@dataclass
class NgramReport:
    n: int
    corpus_docs: int
    max_overlap: float          # 最重叠题面：其 n-gram 命中语料比例
    mean_overlap: float
    top_item: str | None
    top_item_overlap: float
    risk: str = "low"                               # 汇总档（§9.1 阈值机读）
    items_over_threshold: list[str] | None = None   # 逐题越阈（contamination_risk: high）
    word_path: str | None = None                    # "jieba"|"unavailable"；字符路 None

    def as_dict(self) -> dict:
        d = asdict(self)
        if d.get("items_over_threshold") is None:
            d["items_over_threshold"] = []
        return d


def scan_items_overlap(items: list[tuple[str, str]], corpus: set[str], n: int = 8,
                       mode: str = "char", word_path_flag: str | None = None) -> NgramReport:
    """items: [(item_id, 题面)]。返回最大/平均重叠、汇总风险档与逐题越阈清单。

    mode="char"：字符 n-gram（默认 8）；mode="word"：分词 13-gram（需 jieba）。
    word_path_flag：调用方对词路可用性的显式标注（如降级时传 "unavailable"）。
    """
    overlaps: list[tuple[str, float]] = []
    for item_id, text in items:
        grams = word_ngrams(text) if mode == "word" else char_ngrams(text, n=n)
        if not grams:
            overlaps.append((item_id, 0.0))
            continue
        hit = sum(1 for g in grams if g in corpus) / len(grams)
        overlaps.append((item_id, hit))
    flag = word_path_flag  # 调用方对可用性的显式标注（字符路缺省 None，降级时传 unavailable）
    if not overlaps:
        return NgramReport(n=n, corpus_docs=len(corpus), max_overlap=0.0,
                           mean_overlap=0.0, top_item=None, top_item_overlap=0.0,
                           risk="low", items_over_threshold=[], word_path=flag)
    top_id, top_hit = max(overlaps, key=lambda x: x[1])
    mean_hit = sum(h for _, h in overlaps) / len(overlaps)
    over = [iid for iid, h in overlaps if h > RISK_THRESHOLD]
    return NgramReport(n=n, corpus_docs=len(corpus), max_overlap=top_hit,
                       mean_overlap=mean_hit, top_item=top_id, top_item_overlap=top_hit,
                       risk=risk_level(top_hit), items_over_threshold=over, word_path=flag)

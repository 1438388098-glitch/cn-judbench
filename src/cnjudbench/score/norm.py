"""标签归一化与松匹配（真实评测复盘：中文司法输出不能只靠字面全等）。

约定（可审计、确定性，不引入 embedding）：
- 去空白、全半角括号注释、书名号/引号、结尾句读；
- severity 同义表（中高→high 等）；
- 条号抽数字比对（《民法典》第667条、第675条 → {667,675}）；
- 集合命中：归一化后相等 **或** 互为子串（len≥2）。
"""

from __future__ import annotations

import re
from typing import Any

_PAREN = re.compile(r"（[^（）]*）|\([^()]*\)")
_BRACKETS = re.compile(r"[《》「」『』【】\"'“”‘’]")
_TRAIL = re.compile(r"[。．.;；,，、\s]+$")
_WS = re.compile(r"\s+")

SEVERITY_MAP = {
    "high": "high", "h": "high", "高": "high", "较高": "high", "中高": "high",
    "偏高": "high", "重大": "high", "严重": "high",
    "medium": "medium", "m": "medium", "中": "medium", "中等": "medium",
    "一般": "medium", "普通": "medium",
    "low": "low", "l": "low", "低": "low", "较低": "low", "轻微": "low",
}


def normalize_label(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    s = _PAREN.sub("", s)
    s = _BRACKETS.sub("", s)
    s = _TRAIL.sub("", s)
    s = _WS.sub("", s)
    return s.lower() if s.isascii() else s


def normalize_severity(v: Any) -> str:
    key = normalize_label(v)
    return SEVERITY_MAP.get(key, key)


def article_set(v: Any) -> set[str]:
    """从任意条号表述抽数字/之一字条号（含中文数字）。"""
    from ..lawkb.resolve import normalize_article_no

    if v is None:
        return set()
    s = str(v)
    # 先按中文顿号/逗号切段，整段归一，避免「之一」被拆成 1
    out: set[str] = set()
    for part in re.split(r"[、，,；;]", s):
        part = part.strip()
        if not part:
            continue
        n = normalize_article_no(part)
        if n:
            out.add(n)
    if not out:
        parts = re.findall(r"\d+(?:之一|之二|之三)?", s)
        return set(parts) if parts else ({normalize_label(s)} if normalize_label(s) else set())
    return out


_STOP = set("以为的等性与和及或、之一的是了在对向从将予以")


def _core(s: str) -> str:
    """去功能字后的核：以非法占有为目的 → 非法占有目的。"""
    return "".join(ch for ch in s if ch not in _STOP)


def labels_match(got: Any, want: Any) -> bool:
    g, w = normalize_label(got), normalize_label(want)
    if not g or not w:
        return False
    if g == w:
        return True
    if len(w) >= 2 and w in g:
        return True
    if len(g) >= 2 and g in w:
        return True
    gc, wc = _core(g), _core(w)
    if gc and wc and (gc == wc or (len(wc) >= 2 and wc in gc) or (len(gc) >= 2 and gc in wc)):
        return True
    return text_coverage(got, want) >= 0.55


def text_coverage(got: Any, want: Any) -> float:
    """want 二字组在 got 中的覆盖率（长句同义改写的召回代理）。"""
    w = _core(normalize_label(want))
    g = _core(normalize_label(got))
    if not w or not g:
        return 0.0
    if w in g or g in w:
        return 1.0
    grams = [w[i : i + 2] for i in range(max(1, len(w) - 1))] or [w]
    hit = sum(1 for x in set(grams) if x in g)
    return hit / len(set(grams))


def set_f1(got: list | tuple | set | str | None, want: list | tuple | set | str | None) -> tuple[float, int, int]:
    """返回 (f1, tp, |want|)。

    真实输出常见「一句话含多个要件」——want 覆盖采用**非独占**包含匹配
    （任一 got 命中即计）；precision 用 min(1, tp/|got|) 防止长句刷满。
    want 为空 → (1.0, 0, 0) 表示无可比目标（调用方据此跳过/记满）。
    """
    g_list = [x for x in (
        list(got) if isinstance(got, (list, tuple, set)) else ([got] if got not in (None, "") else [])
    ) if x is not None and str(x).strip() != ""]
    w_list = [x for x in (
        list(want) if isinstance(want, (list, tuple, set)) else ([want] if want not in (None, "") else [])
    ) if x is not None and str(x).strip() != ""]
    if not w_list:
        return 1.0, 0, 0
    blob = " | ".join(normalize_label(x) for x in g_list)
    tp = 0
    for w in w_list:
        hit = any(labels_match(g, w) for g in g_list)
        if not hit and blob:
            nw = normalize_label(w)
            if nw and len(nw) >= 2 and nw in blob:
                hit = True
            else:
                # severity 同义
                sw = normalize_severity(w)
                if sw in ("high", "medium", "low") and any(
                    normalize_severity(g) == sw for g in g_list
                ):
                    hit = True
        if hit:
            tp += 1
    prec = min(1.0, tp / len(g_list)) if g_list else 0.0
    rec = tp / len(w_list)
    f1 = 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
    return f1, tp, len(w_list)


# 常用字段键别名（模型中文键 ↔ 金样英文键）
KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "matter_type": ("案件类型", "案由", "matter", "case_type", "纠纷类型"),
    "risk_level": ("风险等级", "风险程度", "risk", "risklevel"),
    "parties": ("当事人", "诉讼地位", "client"),
    "key_facts": ("关键事实", "事实要点", "facts"),
    "next_steps": ("下一步", "后续步骤", "行动建议", "steps"),
    "risk_note": ("风险提示", "风险说明", "风险备注"),
    "issue": ("争点", "争议焦点", "问题"),
    "conclusion": ("结论", "评估结论", "结论意见"),
    "rule_article": ("条号", "法条", "依据条文", "rule_law"),
    "rule_law": ("法名", "法律依据", "依据法律"),
    "application": ("适用分析", "分析", "法律分析"),
    "risk_labels": ("风险标签", "风险点", "risks"),
    "max_severity": ("最高严重度", "severity", "风险级别"),
    "phases_done": ("已完成阶段", "阶段", "phases"),
    "progress": ("进展", "进度"),
    "charge": ("罪名", "涉嫌罪名"),
    "elements": ("要件", "构成要件", "犯罪构成"),
}


def flatten_answer(answer: Any) -> dict:
    """展开常见嵌套容器（case_card / data / result / card），键冲突时浅层优先。"""
    if not isinstance(answer, dict):
        return {}
    out = dict(answer)
    for nest_key in ("case_card", "data", "result", "card", "final", "answer"):
        nest = answer.get(nest_key)
        if isinstance(nest, dict):
            for k, v in nest.items():
                out.setdefault(k, v)
    return out


def find_key(answer: dict, key: str) -> Any:
    if not isinstance(answer, dict):
        return None
    answer = flatten_answer(answer)
    if key in answer:
        return answer[key]
    for alt in KEY_ALIASES.get(key, ()):
        if alt in answer:
            return answer[alt]
    # 宽松：归一化键名相等
    for k, v in answer.items():
        if normalize_label(k) == normalize_label(key):
            return v
        for alt in KEY_ALIASES.get(key, ()):
            if normalize_label(k) == normalize_label(alt):
                return v
    return None

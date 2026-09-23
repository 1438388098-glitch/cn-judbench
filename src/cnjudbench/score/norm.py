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


# 中文数字（含大写金额用字）；仅当数字串后紧跟量词/单位字才转阿拉伯数字，
# 避免误伤「一般」「百分之五十」等非计量词。
_CN_DIG = {"零": 0, "〇": 0, "一": 1, "壹": 1, "二": 2, "两": 2, "贰": 2, "三": 3,
           "叁": 3, "四": 4, "肆": 4, "五": 5, "伍": 5, "六": 6, "陆": 6, "七": 7,
           "柒": 7, "八": 8, "捌": 8, "九": 9, "玖": 9}
_CN_SMALL = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000}
_CN_RUN = re.compile(r"[零〇一二壹二两贰三四叁肆五伍六陆七柒八捌九十拾百佰千仟万]+")
_CN_UNITS = set("元角分厘毫年月日天小时个件次人台辆项笔名口间层条款项章页字张枚位号")

def _cn_run_to_arabic(run: str) -> str | None:
    mult = ""
    if run.endswith(("亿", "万")):  # 万/亿保留为字面乘数：十万 → 10万（非 100000）
        mult = run[-1]
        run = run[:-1]
        if not run:
            return None
    total, num, section = 0, 0, 0
    for ch in run:
        if ch in _CN_DIG:
            num = _CN_DIG[ch]
        elif ch in _CN_SMALL:
            total += (num or 1) * _CN_SMALL[ch]
            num = 0
        else:
            return None
    n = total + num
    return f"{n}{mult}" if n else None

def _norm_quant(s: str) -> str:
    out, last = [], 0
    for m in _CN_RUN.finditer(s):
        nxt = s[m.end()] if m.end() < len(s) else ""
        if nxt not in _CN_UNITS or s[m.end():m.end() + 2] == "分之":
            continue  # 「百分之X」的百不是数量（分在此是分数不是单位）
        conv = _cn_run_to_arabic(m.group(0))
        if conv:
            out.append(s[last:m.start()]); out.append(conv); last = m.end()
    out.append(s[last:])
    return "".join(out)

def normalize_label(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    s = _PAREN.sub("", s)
    s = _BRACKETS.sub("", s)
    s = _TRAIL.sub("", s)
    s = _WS.sub("", s)
    s = _norm_quant(s)
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

    v0.6 改 **1-1 贪心配对**（want 顺序 × got 顺序，确定性）：每个 got 元素
    至多消费一次，tp ≤ min(|got|, |want|)，prec=tp/|got| 自然 ≤1。旧规则
    （非独占 + prec 封顶）允许整段案情塞 1 个元素刷满 F1——u_element 的
    reward hacking 主分不可见。抽取题「拆元素」本身是被测技能：一句话含
    多要件的紧凑写法按 1-1 计部分分，属预期语义（tests/test_setf1_onetoone_v06.py
    金样锁定）。|want|=1 / 精确集 / extra 惩罚等行为不变。
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
    consumed = [False] * len(g_list)

    def _take(pred) -> int | None:
        for i, g in enumerate(g_list):
            if not consumed[i] and pred(g):
                consumed[i] = True
                return i
        return None

    tp = 0
    for w in w_list:
        idx = _take(lambda g: labels_match(g, w))
        if idx is None:
            nw = normalize_label(w)
            if nw and len(nw) >= 2:
                idx = _take(lambda g: nw in normalize_label(g))
        if idx is None:
            sw = normalize_severity(w)
            if sw in ("high", "medium", "low"):
                idx = _take(lambda g: normalize_severity(g) == sw)
        if idx is not None:
            tp += 1
    prec = (tp / len(g_list)) if g_list else 0.0
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

"""基线两列（DESIGN v0.4 §6.3）：random / rules。

- ``random``：输出域内均匀随机（按 item_id 确定性播种，可复现）；
- ``rules``：确定性规则（正则启发 + 法定公式模板），**只读题面与法条锚点，禁读 gold**。

两类答案以模型同构 JSON 产出，经**同一判分管线**（谓词/门禁/role）评分，
故 baseline 分与主分口径可比。工具轨/多轮轨不适用 → n/a。
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from datetime import date, timedelta
from typing import Literal

from .adapters.base import CompletionResult
from .schemas.item import Item

BaselineKind = Literal["random", "rules"]

# cit 期望状态枚举（prompt 契约值域；随机基线在其上均匀猜）
_CIT_STATUSES = ("ok", "wrong_vintage", "not_yet_effective", "unknown_in_lawkb", "unresolved_law")

# s_charge 规则基线的关键词→罪名模板（法条解析器+模板式，禁读 gold）
_CHARGE_RULES = (
    (("窃取", "秘密", "盗窃"), "盗窃罪"),
    (("骗", "虚构", "冒充"), "诈骗罪"),
    (("抢劫", "胁迫", "当场"), "抢劫罪"),
    (("伤害", "重伤", "轻伤"), "故意伤害罪"),
)

# contract 规则基线的风险词表（题面关键词 → 风险标签）
_CONTRACT_RISK_RULES = (
    ("违约金", "违约责任风险"),
    ("解除", "合同解除风险"),
    ("时效", "诉讼时效风险"),
    ("押金", "押金返还风险"),
    ("逾期", "履行逾期风险"),
)


def _rng(item_id: str) -> random.Random:
    return random.Random(int(hashlib.sha256(item_id.encode("utf-8")).hexdigest()[:12], 16))


def _citations(item: Item) -> list[dict]:
    return [{"law": a.law, "article": a.article, "as_of": item.as_of.isoformat()}
            for a in item.law_anchors[:1]]


def _extract_amounts(text: str) -> list[float]:
    out = []
    for m in re.finditer(r"(\d[\d,]*)\s*元", text):
        try:
            out.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return out


def _extract_dates(text: str) -> list[str]:
    out = [m.group(1) for m in re.finditer(r"(\d{4}-\d{2}-\d{2})", text)]
    for m in re.finditer(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text):
        y, mo, d = (int(x) for x in m.groups())
        try:
            out.append(date(y, mo, d).isoformat())
        except ValueError:
            continue
    return out


def _extract_case_no(text: str) -> str | None:
    m = re.search(r"（\d{4}）[^，。；]{2,20}号", text)
    return m.group(0) if m else None


# 《诉讼费用交纳办法》第十三条：≤1万每件50元；其后分段按超额部分累进
_FEE_TIERS = ((100000, 0.025), (200000, 0.02), (500000, 0.015), (1000000, 0.01),
              (2000000, 0.009), (5000000, 0.008), (10000000, 0.007),
              (20000000, 0.006), (float("inf"), 0.005))


def _fee_rule(amount: float) -> int:
    if amount <= 0:
        return 0
    if amount <= 10000:
        return 50
    total, prev = 50.0, 10000.0
    for cap, rate in _FEE_TIERS:
        if amount <= cap:
            total += (amount - prev) * rate
            break
        total += (cap - prev) * rate
        prev = cap
    return max(50, int(total + 0.5))


def random_answer(item: Item) -> str:
    """域内均匀随机答案（确定性播种）。形状合规、内容不解题。"""
    r = _rng(f"{item.id}:random")
    t = item.output_type
    if t == "extract":
        return json.dumps({
            "amount": int(r.uniform(1e3, 1e7)),
            "date": (item.as_of + timedelta(days=r.randint(-365, 365))).isoformat(),
            "case_no": "",
        }, ensure_ascii=False)
    if t == "structured" and item.task_id == "cit_validity":
        return json.dumps({
            "law": item.law_anchors[0].law, "article": item.law_anchors[0].article,
            "as_of": item.as_of.isoformat(), "status": r.choice(_CIT_STATUSES),
        }, ensure_ascii=False)
    if t == "structured" and item.task_id == "s_charge_subsume":
        return json.dumps({
            "charge": r.choice(["盗窃罪", "诈骗罪", "抢劫罪", "故意伤害罪", "职务侵占罪"]),
            "elements": [], "citations": _citations(item), "defendant_name": "",
        }, ensure_ascii=False)
    if t == "structured" and item.task_id == "contract_risk":
        return json.dumps({
            "risk_labels": [r.choice(["违约风险", "时效风险", "解除风险", "执行风险"])],
            "max_severity": r.choice(["high", "medium", "low"]),
            "advice": "建议咨询律师。", "citations": [],
        }, ensure_ascii=False)
    if t == "structured":  # a_irac / long_horizon 等通用结构化兜底
        return json.dumps({
            "issue": "略", "rule_law": item.law_anchors[0].law,
            "rule_article": item.law_anchors[0].article,
            "application": "略", "conclusion": r.choice(["支持", "不予支持"]),
            "citations": _citations(item),
        }, ensure_ascii=False)
    if t == "exact":
        return json.dumps({"answer": str(int(r.uniform(1, 10000))), "steps": []}, ensure_ascii=False)
    return json.dumps({"refuse": False, "note": "random"}, ensure_ascii=False)


def rules_answer(item: Item) -> str:
    """确定性弱规则答案：题面正则启发 + 法定公式模板；禁读 item.gold。"""
    t = item.output_type
    text = item.input
    if t == "extract":
        amounts = _extract_amounts(text)
        dates = _extract_dates(text)
        return json.dumps({
            "amount": amounts[-1] if amounts else 0,
            "date": dates[-1] if dates else item.as_of.isoformat(),
            "case_no": _extract_case_no(text) or "",
        }, ensure_ascii=False)
    if t == "structured" and item.task_id == "cit_validity":
        # 朴素验证器：一律认定引用有效（危险默认，机检会量出它的代价）
        return json.dumps({
            "law": item.law_anchors[0].law, "article": item.law_anchors[0].article,
            "as_of": item.as_of.isoformat(), "status": "ok",
        }, ensure_ascii=False)
    if t == "structured" and item.task_id == "s_charge_subsume":
        charge = next((c for kws, c in _CHARGE_RULES if any(k in text for k in kws)), "诈骗罪")
        return json.dumps({
            "charge": charge, "elements": [], "citations": _citations(item),
            "defendant_name": _extract_case_no(text) or "被告人",
        }, ensure_ascii=False)
    if t == "structured" and item.task_id == "contract_risk":
        risks = [lab for kw, lab in _CONTRACT_RISK_RULES if kw in text] or ["违约责任风险"]
        return json.dumps({
            "risk_labels": risks, "max_severity": "high",
            "advice": "本案存在败诉风险与时效风险，不能保证结果，建议咨询律师。",
            "citations": _citations(item),
        }, ensure_ascii=False)
    if t == "structured":  # a_irac / long_horizon：锚点引用 + IRAC 模板
        a = item.law_anchors[0]
        return json.dumps({
            "issue": text[:40], "rule_law": a.law, "rule_article": a.article,
            "application": f"依《{a.law}》第{a.article}条，结合题面事实涵摄。",
            "conclusion": "部分支持；本案存在举证与执行不能风险，不能保证结果，建议咨询律师。",
            "citations": _citations(item),
        }, ensure_ascii=False)
    if t == "exact":
        # 法定公式规则：题面给标的额 → 分段累进受理费；日期题 → 末个日期启发
        m = re.search(r"标的额\s*(\d[\d,]*)\s*元", text)
        if m:
            return json.dumps({"answer": str(_fee_rule(float(m.group(1).replace(",", "")))),
                               "steps": ["依《诉讼费用交纳办法》第十三条分段累进"]}, ensure_ascii=False)
        dates = _extract_dates(text)
        return json.dumps({"answer": dates[-1] if dates else "", "steps": []}, ensure_ascii=False)
    return json.dumps({"refuse": False, "note": "rules"}, ensure_ascii=False)


SUPPORTED_TASKS = {
    "cit_validity", "u_element_extract", "s_charge_subsume",
    "contract_risk", "a_irac_reason", "long_horizon_case", "gaia_fee_deadline",
}


class _BaselineAdapter:
    """基线适配器：把 random/rules 答案伪装成模型输出走同一条判分管线。"""

    model_id = "baseline"

    def __init__(self, kind: BaselineKind, item: Item) -> None:
        self._kind = kind
        self._item = item
        self.model_id = f"baseline:{kind}"

    def complete(self, prompt: str, *, temperature: float = 0.0, seed: int | None = None) -> CompletionResult:
        fn = random_answer if self._kind == "random" else rules_answer
        text = fn(self._item)
        return CompletionResult(text=text, prompt_tokens=0, completion_tokens=0,
                                latency_ms=0, model_id=self.model_id)


def baseline_adapter_factory(kind: BaselineKind):
    """run_tasks 的 adapter_factory：按题面产出基线答案（同判分管线）。"""
    def _factory(item: Item) -> _BaselineAdapter:
        return _BaselineAdapter(kind, item)
    return _factory

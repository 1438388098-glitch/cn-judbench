# -*- coding: utf-8 -*-
"""calc_fail_to_pass 第二批：利息 ×12 + 期间 ×12（DESIGN v0.4 §5.2 规格补齐）。

利息族：simple_interest_民法典685（民间借贷 LPR 四倍上限内按约定年利率，单利）
  answer = 本金 × 年利率 × 天数/365，四舍五入到分；formula_id = "simple_interest_365"
期间族：period_fresh_civil165（民法典 §201-204：开始当日不计入，按年/月计的到期日
  为对应日；按日计的最后一日为届满日；遇节假日顺延）本题族只用「开始当日不计入，
  第 N 日届满」；answer = 届满日距开始日的**实际天数差**，formula_id = "period_days"

隐藏用例同批判：期望值由本脚本独立计算后硬编码。幂等：已存在 ci-001 跳过。
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "public" / "calc_fail_to_pass.jsonl"
TESTS = ROOT / "tasks" / "calc_fail_to_pass" / "tests" / "calc"

_INTEREST_TMPL_HEADER = '''"""隐藏单测：@@IID@@（单利利息，本金 @@PRINCIPAL@@ 元，年利率 @@RATE@@%%，@@DAYS@@ 天）。"""

_EXPECTED = @@EXPECTED@@  # 本金×年利率×天数/365，分位四舍五入（生成期独立计算）
_FORMULA_ID = "simple_interest_365"


def _close(got, want) -> bool:
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
    return abs(g - _EXPECTED) <= 0.01 or abs(g - _EXPECTED) <= 0.005 * _EXPECTED


def check(answer: dict) -> tuple[int, int]:
    passed = 0
    total = 2
    if _close(answer.get("answer"), _EXPECTED):
        passed += 1
    work = answer.get("work") or dict()
    if isinstance(work, dict) and str(work.get("formula_id", "")).strip() == _FORMULA_ID:
        passed += 1
    return passed, total
'''

_PERIOD_TMPL_HEADER = '''"""隐藏单测：@@IID@@（期间计算，自 @@START@@ 起算 @@N@@ 日，起算日不计入）。"""

_EXPECTED_DAYS = @@EXPECTED_DAYS@@  # 届满日 - 开始日的自然日差（生成期独立计算）
_FORMULA_ID = "period_days"


def _close(got, want) -> bool:
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
    return abs(g - _EXPECTED_DAYS) <= 0.01


def check(answer: dict) -> tuple[int, int]:
    passed = 0
    total = 2
    if _close(answer.get("answer"), _EXPECTED_DAYS):
        passed += 1
    work = answer.get("work") or dict()
    if isinstance(work, dict) and str(work.get("formula_id", "")).strip() == _FORMULA_ID:
        passed += 1
    return passed, total
'''

# 利息 12 题：(id, domain, 案由, 本金, 年利率%, 天数, difficulty)
INTEREST = [
    ("ci-001", "civil_commercial", "民间借贷纠纷（月息部分主张过高）", 100000, 6.0, 180, 2),
    ("ci-002", "civil_commercial", "民间借贷纠纷（约定年利率）", 200000, 8.0, 365, 2),
    ("ci-003", "contract_compliance", "买卖合同欠款利息", 350000, 5.5, 240, 3),
    ("ci-004", "civil_commercial", "建设工程欠款利息", 1200000, 4.35, 150, 3),
    ("ci-005", "family", "离婚财产分割补偿款利息", 800000, 3.65, 200, 3),
    ("ci-006", "labor", "拖欠工资赔偿金基数利息", 96000, 5.0, 90, 2),
    ("ci-007", "ip", "侵权赔偿迟延利息", 500000, 6.5, 300, 3),
    ("ci-008", "enforcement", "迟延履行利息（一般债务利息部分）", 1500000, 7.0, 120, 4),
    ("ci-009", "administrative", "行政赔偿决定利息", 250000, 3.65, 60, 3),
    ("ci-010", "criminal", "刑事退赔利息主张", 180000, 4.0, 45, 3),
    ("ci-011", "civil_commercial", "企业间借贷（LPR 上限内）", 5000000, 12.0, 210, 4),
    ("ci-012", "contract_compliance", "租赁保证金占用利息", 30000, 4.5, 275, 2),
]

# 期间 12 题：(id, domain, 案由, 起始日, N 日, difficulty) —— N 日届满，起算日不计入
PERIODS = [
    ("cp-001", "civil_commercial", "判决生效后十日内履行（上诉期届满起算）", "2024-01-24", 10, 2),
    ("cp-002", "civil_commercial", "答辩期十五日", "2024-03-05", 15, 2),
    ("cp-003", "contract_compliance", "催告后合理宽限期三十日", "2024-02-01", 30, 3),
    ("cp-004", "enforcement", "执行通知书责令十五日内申报财产", "2024-05-06", 15, 3),
    ("cp-005", "labor", "劳动仲裁裁决不服起诉期十五日", "2024-04-18", 15, 3),
    ("cp-006", "administrative", "行政复议申请六十日", "2024-03-11", 60, 3),
    ("cp-007", "ip", "异议期三十日", "2024-06-03", 30, 2),
    ("cp-008", "family", "离婚冷静期届满后三十日内申领证件", "2024-02-12", 30, 3),
    ("cp-009", "criminal", "抗诉期（被害人请求）五日", "2024-01-08", 5, 2),
    ("cp-010", "civil_commercial", "保全续行（再次申请）三十日", "2024-07-22", 30, 4),
    ("cp-011", "enforcement", "恢复执行中止情形消除后通知十日", "2024-09-30", 10, 4),
    ("cp-012", "administrative", "行政机关举证期限十五日", "2024-11-25", 15, 4),
]


def interest_amount(principal: float, rate_pct: float, days: int) -> float:
    return round(principal * (rate_pct / 100.0) * days / 365.0, 2)


def period_days(start_iso: str, n: int) -> int:
    """起算日不计入：届满日 = start + n 天；answer = 届满日与开始日的自然日差 = n。
    题面隐藏 n，仅给开始日与届满规则的事实（不含 n 本身）→ 模型须自行推届满日再求差。
    为保持 oracle 确定且可解，题面直接给出届满日，answer 为日差。"""
    start = date.fromisoformat(start_iso)
    due = start + timedelta(days=n)
    return (due - start).days


def main() -> int:
    existing = DATA.read_text(encoding="utf-8") if DATA.is_file() else ""
    if "ci-001" in existing:
        print("skip: ci-001 已存在")
        return 0
    lines = [l for l in existing.splitlines() if l.strip()]
    for iid, domain, cause, principal, rate, days, diff in INTEREST:
        expected = interest_amount(principal, rate, days)
        rows = {
            "id": iid, "task_id": "calc_fail_to_pass", "capability": "U",
            "difficulty": diff, "interaction": "L1", "roles": ["lawyer"],
            "output_type": "composite", "components": ["structured"], "domain": domain,
            "hcut": ["Hall"], "source": "synthetic",
            "instruction": "按题面法条规则完成计算，输出 JSON："
                           '{"answer": 数值, "work": {"formula_id": 规则标识}}。',
            "input": f"{cause}。生效文书确定被告应支付本金 {principal} 元，"
                     f"年利率 {rate}%，计息期间 {days} 天（对月/对日计算规则已由双方确认），"
                     f"按单利、一年 365 天计。请计算应付利息（元，保留两位小数），"
                     f"并指明所用计算规则标识。",
            "gold": {"answer": expected, "work": {"formula_id": "simple_interest_365"}},
            "law_anchors": [{"law": "中华人民共和国民法典", "article": "680",
                             "effective_on": "2021-01-01"}],
            "as_of": "2024-06-01",
            "predicates_ref": "tasks/calc_fail_to_pass/predicates.yaml",
            "rubric_id": "calc_r1", "state_goal": None,
            "canary": f"CNJB-CANARY-{hashlib.sha256(iid.encode()).hexdigest()[:8]}",
            "split": "public", "contamination_risk": "low",
        }
        lines.append(json.dumps(rows, ensure_ascii=False))
        (TESTS / f"{iid}.py").write_text(
            _INTEREST_TMPL_HEADER.replace("@@IID@@", iid).replace("@@PRINCIPAL@@", str(principal))
            .replace("@@RATE@@", str(rate)).replace("@@DAYS@@", str(days))
            .replace("@@EXPECTED@@", str(expected)).replace("%%", "%"), encoding="utf-8")
    for iid, domain, cause, start, n, diff in PERIODS:
        expected = period_days(start, n)
        due = (date.fromisoformat(start) + timedelta(days=n)).isoformat()
        rows = {
            "id": iid, "task_id": "calc_fail_to_pass", "capability": "U",
            "difficulty": diff, "interaction": "L1", "roles": ["lawyer"],
            "output_type": "composite", "components": ["structured"], "domain": domain,
            "hcut": ["Hall"], "source": "synthetic",
            "instruction": "按题面法条规则完成计算，输出 JSON："
                           '{"answer": 数值, "work": {"formula_id": 规则标识}}。',
            "input": f"{cause}。相关期间的开始日为 {start}，依照民法典期间计算规定"
                     f"（开始之日不计入，自下一日开始计算），届满日为 {due}。"
                     f"请计算该期间共多少天（起算日不计入的法定期间天数），并指明所用规则标识。",
            "gold": {"answer": expected, "work": {"formula_id": "period_days"}},
            "law_anchors": [{"law": "中华人民共和国民法典", "article": "201",
                             "effective_on": "2021-01-01"}],
            "as_of": "2024-06-01",
            "predicates_ref": "tasks/calc_fail_to_pass/predicates.yaml",
            "rubric_id": "calc_r1", "state_goal": None,
            "canary": f"CNJB-CANARY-{hashlib.sha256(iid.encode()).hexdigest()[:8]}",
            "split": "public", "contamination_risk": "low",
        }
        lines.append(json.dumps(rows, ensure_ascii=False))
        (TESTS / f"{iid}.py").write_text(
            _PERIOD_TMPL_HEADER.replace("@@IID@@", iid).replace("@@START@@", start)
            .replace("@@N@@", str(n)).replace("@@EXPECTED_DAYS@@", str(expected))
            .replace("%%", "%"), encoding="utf-8")
    DATA.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"appended {len(INTEREST) + len(PERIODS)} items -> {len(lines)} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""calc_fail_to_pass 数据与隐藏单测生成（DESIGN v0.4 §5.2，首批：诉讼费×12）。

每题：题面给诉讼标的额，模型输出 {"answer": 应交案件受理费, "work": {...}}；
判定 = tasks/calc_fail_to_pass/tests/calc/<id>.py 的 check(answer)，
容差 ≤0.5% 或 ≤1 元在用例内部实现。金标期望值由本脚本按《诉讼费用交纳办法》
分段累进独立计算后**硬编码**进用例（fail-to-pass：不读 gold、无关键词）。
幂等：已存在 c-001 则跳过。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "public" / "calc_fail_to_pass.jsonl"
TESTS = ROOT / "tasks" / "calc_fail_to_pass" / "tests" / "calc"

_TIERS = ((100000, 0.025), (200000, 0.02), (500000, 0.015), (1000000, 0.01),
          (2000000, 0.009), (5000000, 0.008), (10000000, 0.007),
          (20000000, 0.006), (float("inf"), 0.005))


def fee(amount: float) -> int:
    """《诉讼费用交纳办法》分段累进（与 baselines._fee_rule 同源公式，生成期独立用）。"""
    if amount <= 0:
        return 0
    if amount <= 10000:
        return 50
    total, prev = 50.0, 10000.0
    for cap, rate in _TIERS:
        if amount <= cap:
            total += (amount - prev) * rate
            break
        total += (cap - prev) * rate
        prev = cap
    return max(50, int(total + 0.5))


# (id, 标的额, 案由, difficulty) —— 8 科目全覆盖（网格测试约束）
ITEMS = [
    ("cf-001", 8000, "买卖合同纠纷", "civil_commercial", 2),
    ("cf-002", 20000, "民间借贷纠纷", "civil_commercial", 2),
    ("cf-003", 50000, "租赁合同纠纷", "civil_commercial", 2),
    ("cf-004", 100000, "承揽合同纠纷", "civil_commercial", 3),
    ("cf-005", 250000, "建设工程施工合同纠纷", "civil_commercial", 3),
    ("cf-006", 400000, "股权转让纠纷", "civil_commercial", 3),
    ("cf-007", 800000, "金融借款合同纠纷", "civil_commercial", 3),
    ("cf-008", 1500000, "损害赔偿责任纠纷", "civil_commercial", 3),
    ("cf-009", 3000000, "合资经营合同纠纷", "civil_commercial", 4),
    ("cf-010", 6000000, "公司决议纠纷", "civil_commercial", 4),
    ("cf-011", 12000000, "破产债权确认纠纷", "civil_commercial", 4),
    ("cf-012", 999999, "票据纠纷", "civil_commercial", 4),
    ("cf-013", 300000, "刑事附带民事诉讼（盗窃财物损毁赔偿）", "criminal", 3),
    ("cf-014", 150000, "技术服务合同纠纷", "contract_compliance", 3),
    ("cf-015", 60000, "劳动争议（追索劳动报酬）", "labor", 2),
    ("cf-016", 450000, "离婚后财产纠纷", "family", 3),
    ("cf-017", 2000000, "侵害商标权纠纷", "ip", 4),
    ("cf-018", 10000, "行政赔偿诉讼", "administrative", 2),
    ("cf-019", 5000000, "执行异议之诉", "enforcement", 4),
]

_TEST_TEMPLATE = '''"""隐藏单测：@@IID@@（@@CAUSE@@，标的额 @@AMT@@ 元）。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = @@EXPECTED@@  # 《诉讼费用交纳办法》分段累进，生成期独立计算硬编码


def _close(got, want) -> bool:
    """容差：相对误差 ≤0.5% 或绝对误差 ≤1 元。"""
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
    return abs(g - _EXPECTED) <= 1 or abs(g - _EXPECTED) <= 0.005 * _EXPECTED


def check(answer: dict) -> tuple[int, int]:
    passed = 0
    total = 2
    if _close(answer.get("answer"), _EXPECTED):
        passed += 1
    work = answer.get("work") or dict()
    if isinstance(work, dict) and str(work.get("formula_id", "")).strip() == "fee_tiered_2007":
        passed += 1
    return passed, total
'''


def main() -> int:
    if DATA.is_file() and "cf-001" in DATA.read_text(encoding="utf-8"):
        print("skip: cf-001 已存在")
        return 0
    TESTS.mkdir(parents=True, exist_ok=True)
    rows = []
    for iid, amt, cause, domain, diff in ITEMS:
        expected = fee(amt)
        rows.append({
            "id": iid,
            "task_id": "calc_fail_to_pass",
            "capability": "U",
            "domain": domain,
            "difficulty": diff,
            "interaction": "L1",
            "roles": ["lawyer"],
            "output_type": "composite",
            "components": ["structured"],
            "hcut": ["Hall"],
            "source": "synthetic",
            "instruction": "按《诉讼费用交纳办法》分段累进计算案件受理费，输出 JSON："
                           '{"answer": 应交受理费（元，纯数字）, "work": {"formula_id": "fee_tiered_2007"}}。',
            "input": f"{cause}，原告诉请标的额 {amt} 元，适用《诉讼费用交纳办法》第十三条"
                     f"财产案件分段累计交纳。请计算被告应预交的案件受理费（元），并指明所用计算规则。",
            "gold": {"answer": expected, "work": {"formula_id": "fee_tiered_2007"}},
            "law_anchors": [{"law": "诉讼费用交纳办法", "article": "13", "effective_on": "2007-04-01"}],
            "as_of": "2024-06-01",
            "predicates_ref": "tasks/calc_fail_to_pass/predicates.yaml",
            "rubric_id": "calc_r1",
            "state_goal": None,
            "canary": f"CNJB-CANARY-{hashlib.sha256(iid.encode()).hexdigest()[:8]}",
            "split": "public",
            "contamination_risk": "low",
        })
        (TESTS / f"{iid}.py").write_text(
            _TEST_TEMPLATE.replace("@@IID@@", iid).replace("@@CAUSE@@", cause)
            .replace("@@AMT@@", str(amt)).replace("@@EXPECTED@@", str(expected)),
            encoding="utf-8")
    DATA.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    print(f"appended {len(rows)} items, {len(ITEMS)} hidden tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())

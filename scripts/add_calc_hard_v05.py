"""v0.5 Phase 3b：calc_fail_to_pass 计算硬变体（cx-001..008）。

DESIGN §3b 三族（审计实证失分轴：复利整族 50、期间嵌套、封顶叠加）：
- 期间嵌套 2：30 日期末日遇元旦顺延（cx-001）、时效中断重新起算顺延
  天数（cx-002）——起算/顺延/对应日口径全部在题面给定（cp-001 契约：
  answer 为天数，日期歧义不上机）；
- 封顶叠加 2：部分还款冲抵本金后分段上限计息（cx-003）、上限锁定
  合同成立时 LPR（cx-004 题面给两个 LPR 逼选择）；
- 复利深化 4：年复利×上限利率（cx-005）、利息/违约金竞合择高
  （cx-006）、半年复利×中期部分还款冲抵（cx-007）、复利总额封顶
  （cx-008）。

契约（tasks/calc_fail_to_pass/reference.md）：
- 期望值由本脚本在生成期独立计算后硬编码进隐藏用例，判分路径不读 gold；
- gold 与隐藏用例同真由 tests/test_calc_task.py 逐题断言锁定；
- 新增 6 个 formula_id 已同步 tasks/calc_fail_to_pass/task.yaml 的
  answer_enums 与 prompt_template 枚举（v0.4.1 公平性教训）。

用法::

    python scripts/add_calc_hard_v05.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ITEMS_PATH = REPO / "data" / "public" / "calc_fail_to_pass.jsonl"
TESTS_DIR = REPO / "tasks" / "calc_fail_to_pass" / "tests" / "calc"

CC = "中华人民共和国民法典"

# ---- 生成期独立计算（期望值唯一来源，写进 item.gold 与隐藏用例）----


def cx001_expected() -> float:
    """30 日期自 2021-12-03 起算，末日 2022-01-01（元旦）顺延至 01-04；
    实际占用自然日 12-03..01-04 含首尾 = 29 + 4 = 33。"""
    return 29 + 4


def cx002_expected() -> float:
    """原届满 2023-12-31，中断后新届满 2024-06-16；
    顺延自然日 = 2024-01-01 起算 31+29+31+30+31+16 = 168。"""
    return 31 + 29 + 31 + 30 + 31 + 16


def cx003_expected() -> float:
    """段1 200000×15.4%×180/365；段2 100000×15.4%×184/365。"""
    seg1 = 200000 * 0.154 * 180 / 365
    seg2 = 100000 * 0.154 * 184 / 365
    return round(seg1 + seg2, 2)


def cx004_expected() -> float:
    """上限按合同成立时 3.85%×4=15.4%（非起诉时 3.45%）；730 天单利。"""
    return round(150000 * 0.154 * 730 / 365, 2)


def cx005_expected() -> float:
    """年复利两年、有效利率=上限 15.4%：100000×(1.154²−1)。"""
    return round(100000 * (1.154 ** 2 - 1), 2)


def cx006_expected() -> float:
    """单利利息 200000×10%×2=40000 与违约金 35000 择高。"""
    return float(max(200000 * 0.10 * 2, 35000))


def cx007_expected() -> float:
    """半年复利 3% 共6期：期1息3000（资本化）；期2息3090；还60090冲息3090+冲本57000
    → 余本46000；期3..6息 1380/1421.40/1464.04/1507.96；合计 11863.40。"""
    p = 100000.0
    i1 = round(p * 0.03, 2)
    p2 = round(p + i1, 2)
    i2 = round(p2 * 0.03, 2)
    remain = round(p2 + i2 - 60090, 2)   # 46000
    total = round(i1 + i2, 2)
    for _ in range(4):
        i = round(remain * 0.03, 2)
        total = round(total + i, 2)
        remain = round(remain + i, 2)
    return total


def cx008_expected() -> float:
    """复利利息 300000×(1.08³−1)=77913.60 超过封顶 60000 → 按封顶。"""
    interest = round(300000 * (1.08 ** 3 - 1), 2)
    return float(min(interest, 60000))


ITEMS = [
    dict(
        id="cx-001", domain="civil_commercial", formula="period_days",
        input="合同约定「验收合格后30日内付款」。验收合格日为 2021-12-02，依照民法典期间"
        "计算规定（开始之日不计入，自次日开始计算），付款期间自 2021-12-03 起算，名义"
        "末日为 2022-01-01；该日及次日（2022-01-01 至 2022-01-03）为法定休假日，依民法典"
        "规定以休假日结束的次日为期间最后一日，即顺延后届满日为 2022-01-04。请计算该"
        "期间实际占用的自然日天数（自 2021-12-03 起至顺延后届满日止，含首尾），并指明"
        "所用规则标识。",
        gold=33.0, anchors=[(CC, "201")],
    ),
    dict(
        id="cx-002", domain="civil_commercial", formula="period_days",
        input="借款于 2020-12-31 到期，三年诉讼时效自 2021-01-01 起算，原届满日为 "
        "2023-12-31。债权人于 2021-06-15 书面催收构成诉讼时效中断，时效自 2021-06-16 "
        "重新起算，重新起算后的届满日为 2024-06-16（对应日口径依题面给定）。请计算新"
        "届满日较原届满日顺延的自然日天数（2023-12-31 至 2024-06-16 的自然日差），并"
        "指明所用规则标识。",
        gold=168.0, anchors=[(CC, "188")],
    ),
    dict(
        id="cx-003", domain="civil_commercial", formula="interest_cap_offset_365",
        input="民间借贷纠纷。借款本金 200000 元于 2021-01-10 放款，约定年利率 20%，利率"
        "保护上限为合同成立时一年期 LPR 的四倍（15.4%），超限部分不受保护。2021-07-10 "
        "借款人还款 100000 元，双方确认全部冲抵本金。借款 2022-01-10 到期，利息按实际"
        "占用本金分段单利计算（一年 365 天：第一段 2021-01-11 至 2021-07-10 共 180 天，"
        "第二段 2021-07-11 至 2022-01-10 共 184 天）。请计算应付利息总额（元，保留两位"
        "小数），并指明所用规则标识。",
        gold=None, anchors=[(CC, "676")],  # gold 由本脚本计算回填
    ),
    dict(
        id="cx-004", domain="civil_commercial", formula="interest_cap_formation",
        input="借款本金 150000 元，2020-09-01 订立合同并放款，约定年利率 18%，期限两年"
        "（按 730 天计），单利、一年 365 天。利率保护上限为合同成立时一年期 LPR 的四倍；"
        "题面给定：合同成立时一年期 LPR 为 3.85%（四倍 15.4%），债权人起诉时（2023 年）"
        "一年期 LPR 为 3.45%（四倍 13.8%）。请计算受法律保护的利息总额（元，保留两位"
        "小数），并指明所用规则标识。",
        gold=None, anchors=[(CC, "676")],
    ),
    dict(
        id="cx-005", domain="civil_commercial", formula="compound_annual_cap",
        input="借款本金 100000 元，约定年利率 16%，按年复利计息两年（利息滚入本金）。"
        "利率保护上限为合同成立时一年期 LPR 的四倍（15.4%），复利计算以该上限利率为"
        "有效利率。请计算两年后应付利息总额（利息部分，元，保留两位小数），并指明"
        "所用规则标识。",
        gold=None, anchors=[(CC, "680")],
    ),
    dict(
        id="cx-006", domain="civil_commercial", formula="remedy_max_interest_penalty",
        input="借款本金 200000 元逾期两年。合同约定：债务人逾期时，债权人可主张按年利率"
        " 10% 的单利计算两年逾期利息，或主张一次性违约金 35000 元，两者以高者为准。请"
        "计算债权人可主张的金额（元，保留两位小数），并指明所用规则标识。",
        gold=None, anchors=[(CC, "585")],
    ),
    dict(
        id="cx-007", domain="civil_commercial", formula="compound_semiannual_offset",
        input="借款本金 100000 元，年利率 6%，按半年复利计息三年（每半年计息一次，"
        "期内利率 3%）。第 2 期期末，借款人支付 60090 元，双方确认优先冲抵当期利息、"
        "余额冲抵本金。请计算三年期间借款人实际支付的利息总额（元，保留两位小数），"
        "并指明所用规则标识。",
        gold=None, anchors=[(CC, "676")],
    ),
    dict(
        id="cx-008", domain="civil_commercial", formula="compound_interest_total_cap",
        input="借款本金 300000 元，约定年利率 8% 按年复利计息三年（利息滚入本金）；"
        "同时约定利息总额以本金 60000 元为上限封顶。请计算借款人应付利息总额（元，"
        "保留两位小数），并指明所用规则标识。",
        gold=None, anchors=[(CC, "509")],
    ),
]

COMPUTE = {
    "cx-001": cx001_expected,
    "cx-002": cx002_expected,
    "cx-003": cx003_expected,
    "cx-004": cx004_expected,
    "cx-005": cx005_expected,
    "cx-006": cx006_expected,
    "cx-007": cx007_expected,
    "cx-008": cx008_expected,
}

TEST_DOC = {
    "cx-001": "期间嵌套：30 日期末日 2022-01-01 遇元旦顺延至 01-04，实际占用 33 天（未顺延 30 判错）",
    "cx-002": "时效中断重新起算：2023-12-31→2024-06-16 顺延 168 天（不中断 0 / 顺延口径错均判错）",
    "cx-003": "封顶×部分还款冲抵本金分段计息（约定 20% 超上限须按 15.4%；未冲抵 30715.62 判错）",
    "cx-004": "上限锁定合同成立时 LPR 15.4%（误用起诉时 13.8%→41400 判错；误用约定 18%→54000 判错）",
    "cx-005": "年复利两年以 15.4% 为有效利率（无视封顶 34560 / 误单利 30800 均判错）",
    "cx-006": "利息 40000 与违约金 35000 竞合择高（取低 35000 / 误复利 42000 均判错）",
    "cx-007": "半年复利+第2期末部分还款冲抵：三年6期利息总额 11863.40（只计3期 7470 / 误单利 9000 判错）",
    "cx-008": "复利利息 77913.60 超约定总额封顶按 60000（无视封顶 77913.60 / 误单利 72000 判错）",
}


def _write_test(item_id: str, expected: float, formula: str, note: str) -> None:
    # 期间/天数用严格容差（差一天即法律意义不同）；金额沿用 ≤1 元或 ≤0.5%
    if formula == "period_days":
        close_body = "    return abs(g - float(want)) <= 0.01"
    else:
        close_body = ("    return abs(g - float(want)) <= 1 "
                      "or abs(g - float(want)) <= 0.005 * float(want)")
    text = f'''"""隐藏单测：{item_id}（{note}）。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = {expected!r}
_FORMULA_ID = {formula!r}


def _close(got, want) -> bool:
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
{close_body}


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
    (TESTS_DIR / f"{item_id}.py").write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    items = [json.loads(l) for l in ITEMS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    existing = {it["id"] for it in items}
    added = []
    for spec in ITEMS:
        expected = COMPUTE[spec["id"]]()
        _write_test(spec["id"], expected, spec["formula"], TEST_DOC[spec["id"]])
        if spec["id"] in existing:
            print(f"skip item（已存在，隐藏用例已刷新）: {spec['id']}")
            continue
        expected = COMPUTE[spec["id"]]()
        gold = spec["gold"] if spec["gold"] is not None else expected
        it = {
            "id": spec["id"],
            "task_id": "calc_fail_to_pass",
            "capability": "U",
            "difficulty": 4,
            "interaction": "L1",
            "roles": ["lawyer"],
            "output_type": "composite",
            "components": ["structured"],
            "domain": spec["domain"],
            "hcut": ["Hall"],
            "source": "synthetic",
            "instruction": "按题面法条规则完成计算，输出 JSON：{\"answer\": 数值, \"work\": {\"formula_id\": 规则标识}}。",
            "input": spec["input"],
            "gold": {"answer": gold, "work": {"formula_id": spec["formula"]}},
            "law_anchors": [
                {"law": law, "article": article, "effective_on": "2021-01-01"}
                for law, article in spec["anchors"]
            ],
            "as_of": "2024-06-01",
            "predicates_ref": "tasks/calc_fail_to_pass/predicates.yaml",
            "rubric_id": "calc_r1",
            "state_goal": None,
            "canary": f"CNJB-CANARY-{0x7E30 + len(added):08x}",
            "split": "public",
            "contamination_risk": "low",
        }
        items.append(it)
        added.append((spec["id"], gold))
    ITEMS_PATH.write_text(
        "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items),
        encoding="utf-8",
    )
    for iid, g in added:
        print(f"added {iid} gold={g}")
    print(f"total {len(items)} -> {ITEMS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

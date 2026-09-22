# -*- coding: utf-8 -*-
"""calc hard 变体（DESIGN v0.4 §5.2 硬度阶梯）：复利 / 保全费 / 节假日顺延届满日。

每题同时生成题面（data/public/calc_fail_to_pass.jsonl 追加）与隐藏单测
（tasks/calc_fail_to_pass/tests/calc/<id>.py，期望值生成期独立硬编码）。
prompt 枚举与 task.yaml answer_enums 已扩至 5 个 formula_id。幂等（按 id 查重）。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "public" / "calc_fail_to_pass.jsonl"
TESTS = ROOT / "tasks" / "calc_fail_to_pass" / "tests" / "calc"

TEST_TEMPLATE = (
    '"""隐藏单测：{iid}（{hint}）。fail-to-pass oracle，禁读 gold。"""\n'
    "\n"
    "_EXPECTED = {expected!r}  # 生成期独立计算硬编码\n"
    "_FORMULA_ID = {formula!r}\n"
    "\n"
    "\n"
    "def _close(got, want) -> bool:\n"
    "{close_impl}"
    "    return False\n"
    "\n"
    "\n"
    "def check(answer: dict) -> tuple[int, int]:\n"
    "    passed = 0\n"
    "    total = 2\n"
    "    if _close(answer.get(\"answer\"), _EXPECTED):\n"
    "        passed += 1\n"
    "    work = answer.get(\"work\") or dict()\n"
    "    if isinstance(work, dict) and str(work.get(\"formula_id\", \"\")).strip() == _FORMULA_ID:\n"
    "        passed += 1\n"
    "    return passed, total\n"
)

NUM_CLOSE = (
    "    try:\n"
    "        g = float(got)\n"
    "    except (TypeError, ValueError):\n"
    "        return False\n"
    "    return abs(g - float(want)) <= 1 or abs(g - float(want)) <= 0.005 * float(want)\n"
)

DATE_CLOSE = (
    "    try:\n"
    "        import re as _re\n"
    "    except ImportError:\n"
    "        return False\n"
    "    got_s = got.strip() if isinstance(got, str) else \"\"\n"
    "    return bool(_re.fullmatch(r\"\\d{4}-\\d{2}-\\d{2}\", got_s)) and got_s == str(want)\n"
)

# (id, domain, difficulty, input, expected, formula_id, hint, is_date)
ROWS = [
    ("ci-hard-001", "civil_commercial", 4,
     "借款本金 200000 元，约定年利率 6%，按半年复利计息，借期 3 年整，到期一次性还本付息。"
     "计算到期应付利息额（元，保留两位小数），并指出所用规则标识。",
     round(200000 * ((1 + 0.06 / 2) ** 6) - 200000, 2),
     "compound_interest_semiannual",
     "半年复利 6 期利息 = 200000×(1.03)^6−200000 = 38810.46；答本息和 238810.46 判错", False),
    ("cf-hard-001", "enforcement", 4,
     "当事人申请财产保全，保全财产数额 300000 元。按《诉讼费用交纳办法》第十四条计算"
     "财产保全申请费（元，保留两位小数；注意基础件费与分段费率，封顶规则另行核验），并指出所用规则标识。",
     2020.0,
     "fee_preservation_2007",
     "保全费 = 30 + (100000-1000)×1% + (300000-100000)×0.5% = 2020；误用受理费 5800 判错", False),
    ("cp-hard-001", "administrative", 4,
     "2024-04-01 送达一审判决书，当事人不服提起上诉。上诉期为判决送达之日起 30 日"
     "（期间起算日不计入；届满日遇法定节假日的，顺延至节假日后的第一个工作日）。"
     "按 2024 年国务院办公厅放假安排（劳动节 5 月 1 日至 5 日放假）给出上诉期届满日"
     "（YYYY-MM-DD），并指出所用规则标识。",
     "2024-05-06",
     "period_days",
     "4/2 起第 30 日为 5/1（劳动节）→ 顺延至 5/6；答 5/1 或仅按周末顺延 5/2 均判错", True),
]


def main() -> int:
    lines = [l for l in DATA.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    have = {json.loads(l)["id"] for l in lines}
    for iid, domain, diff, inp, expected, formula, hint, is_date in ROWS:
        if iid in have:
            print(f"skip {iid} (exists)")
            continue
        gold_answer = (str(expected) if is_date else
                       (str(int(expected)) if float(expected).is_integer()
                        else f"{expected:.2f}"))
        item = {
            "id": iid, "task_id": "calc_fail_to_pass", "capability": "U",
            "difficulty": diff, "interaction": "L1", "roles": ["lawyer", "party"],
            "output_type": "composite", "hcut": ["Cons"], "source": "synthetic",
            "domain": domain,
            "instruction": "按题目完成司法计算，answer 给数值/日期，work.formula_id 给规则标识。",
            "input": inp,
            "gold": {"calls": [], "answer": gold_answer,
                     "work": {"formula_id": formula}},
            "components": ["structured"],
            "law_anchors": [{"law": "中华人民共和国民事诉讼法", "article": "122",
                             "effective_on": "2024-01-01"}],
            "as_of": "2024-06-01",
            "predicates_ref": "tasks/calc_fail_to_pass/predicates.yaml",
            "rubric_id": "calc_r1", "state_goal": None,
            "canary": f"CNJB-CANARY-{hashlib.sha256(iid.encode()).hexdigest()[:8]}",
            "split": "public", "contamination_risk": "low",
        }
        lines.append(json.dumps(item, ensure_ascii=False))
        test_src = TEST_TEMPLATE.format(
            iid=iid, hint=hint, expected=expected, formula=formula,
            close_impl=DATE_CLOSE if is_date else NUM_CLOSE)
        (TESTS / f"{iid}.py").write_text(test_src, encoding="utf-8", newline="\n")
        print(f"added {iid} (expected={expected!r})")
    DATA.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"total items: {len(lines)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

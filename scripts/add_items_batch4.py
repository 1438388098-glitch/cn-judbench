# -*- coding: utf-8 -*-
"""第四批扩库（c126）：cit_validity stale 族 6 题——「同一引用，as_of 翻转效力」。

设计（全部经 lawkb resolve_article 逐一验证，2026-09-23）：
- cit-022 民法总则 188 @2024-06-01 → wrong_vintage（2021-01-01 废止，替代=民法典 188）
- cit-023 民法总则 188 @2020-06-01 → ok（gp_188_2017 窗口内；与 022 对偶）
- cit-024 继承法 10 @2024-06-01 → wrong_vintage（继承法废止）
- cit-025 继承法 10 @2020-06-01 → ok（suc_10_1985；与 024 对偶）
- cit-026 合同法解释（二）26 @2020-06-01 → ok（废止前有效：后来废止不溯及当时——陷阱题）
- cit-027 刑法 253之一 @2014-06-01 → ok（cl_253z1_2009，修正案九 2015-11-01 前旧版在窗——
  「存在新版本」≠「当时无效」，防 wrong_vintage 过判）

纪律：gold 每题恰 1 引用（status_ladder 只判 gold[0]）；canary cd01..cd06；
source=synthetic；锚 effective_on 一律取所引版本窗口内日期（audit_anchors
第 8 步按锚自身时点解析，在窗即不触发硬失败）。用法::

    python scripts/add_items_batch4.py
"""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "public" / "cit_validity.jsonl"

BASE = {
    "interaction": "L1",
    "roles": ["lawyer"],
    "output_type": "structured",
    "hcut": ["Hall"],
    "source": "synthetic",
    "rubric_id": None,
    "state_goal": None,
    "split": "public",
    "contamination_risk": "low",
    "task_id": "cit_validity",
    "capability": "Cit",
    "instruction": "判断引用在 as_of 是否有效，按任务 prompt_template 输出 JSON。",
    "predicates_ref": "tasks/cit_validity/predicates.yaml",
}

ZZZ = "中华人民共和国民法总则"
SUC = "中华人民共和国继承法"
CTR2 = "最高人民法院关于适用《中华人民共和国合同法》若干问题的解释（二）"
XL = "中华人民共和国刑法"

ITEMS = [
    dict(BASE, id="cit-022", domain="civil_commercial", difficulty=3,
         input="引用：民法总则 第一百八十八条（普通诉讼时效）；as_of：2024-06-01。",
         gold=[{"law": "民法总则", "article": "188", "as_of": "2024-06-01",
                "expect_status": "wrong_vintage"}],
         law_anchors=[{"law": ZZZ, "article": "188", "effective_on": "2017-10-01"}],
         as_of="2024-06-01", canary="CNJB-CANARY-cd01"),
    dict(BASE, id="cit-023", domain="civil_commercial", difficulty=3,
         input="引用：民法总则 第一百八十八条（普通诉讼时效）；as_of：2020-06-01。",
         gold=[{"law": "民法总则", "article": "188", "as_of": "2020-06-01",
                "expect_status": "ok"}],
         law_anchors=[{"law": ZZZ, "article": "188", "effective_on": "2017-10-01"}],
         as_of="2020-06-01", canary="CNJB-CANARY-cd02"),
    dict(BASE, id="cit-024", domain="family", difficulty=3,
         input="引用：继承法 第十条（法定继承顺序）；as_of：2024-06-01。",
         gold=[{"law": "继承法", "article": "10", "as_of": "2024-06-01",
                "expect_status": "wrong_vintage"}],
         law_anchors=[{"law": SUC, "article": "10", "effective_on": "1985-10-01"}],
         as_of="2024-06-01", canary="CNJB-CANARY-cd03"),
    dict(BASE, id="cit-025", domain="family", difficulty=3,
         input="引用：继承法 第十条（法定继承顺序）；as_of：2020-06-01。",
         gold=[{"law": "继承法", "article": "10", "as_of": "2020-06-01",
                "expect_status": "ok"}],
         law_anchors=[{"law": SUC, "article": "10", "effective_on": "1985-10-01"}],
         as_of="2020-06-01", canary="CNJB-CANARY-cd04"),
    dict(BASE, id="cit-026", domain="civil_commercial", difficulty=4,
         input="引用：合同法解释（二）第二十六条（情势变更）；as_of：2020-06-01。",
         gold=[{"law": "合同法解释（二）", "article": "26", "as_of": "2020-06-01",
                "expect_status": "ok"}],
         law_anchors=[{"law": CTR2, "article": "26", "effective_on": "2009-05-13"}],
         as_of="2020-06-01", canary="CNJB-CANARY-cd05"),
    dict(BASE, id="cit-027", domain="criminal", difficulty=4,
         input="引用：刑法 第二百五十三条之一（侵犯公民个人信息罪）；as_of：2014-06-01。",
         gold=[{"law": "刑法", "article": "253之一", "as_of": "2014-06-01",
                "expect_status": "ok"}],
         law_anchors=[{"law": XL, "article": "253之一", "effective_on": "2009-02-28"}],
         as_of="2014-06-01", canary="CNJB-CANARY-cd06"),
]


def main() -> int:
    existing = {json.loads(l)["id"] for l in PATH.read_text(encoding="utf-8-sig").splitlines() if l.strip()}
    clash = [it["id"] for it in ITEMS if it["id"] in existing]
    if clash:
        raise SystemExit(f"id 已存在，拒绝重复追加: {clash}")
    with PATH.open("a", encoding="utf-8") as f:
        for it in ITEMS:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"appended {len(ITEMS)} items -> {PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

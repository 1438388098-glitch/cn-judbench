"""R17：a_irac_reason hard 子集——6 题复合争点，压头部模型满分率。

背景：R16 实测 a_irac 16/19 满分（86.84），违反中间带满分率 ≤25% 目标。
本批 6 题（ah-001..006）每题埋一个复合考点：请求权竞合选择、保证期间经过、
表见代理认定、违约金/定金/不可抗力择一、民法典溯及力（持续性法律事实）、
建设工程价款优先受偿。gold 配 acceptable_articles 多解口径（R16 引入），
配套 lawkb 条文由 scripts/add_lawkb_laws_r16.py 的 R17 段落提供。

题目为自拟合成题（source=synthetic，contamination_risk=low），考点对应的
规范均为现行有效通说条文。用法::

    python scripts/add_airac_hard_r17.py
"""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "public" / "a_irac_reason.jsonl"

CC = "中华人民共和国民法典"
TEMPORAL = "最高人民法院关于适用中华人民共和国民法典时间效力的若干规定"


def _item(idx: int, id_: str, domain: str, input_: str, issue: str, law: str, article: str,
          application: str, acceptable: list[tuple[str, str]], eff: str) -> dict:
    return {
        "difficulty": 4,
        "interaction": "L1",
        "roles": ["lawyer"],
        "output_type": "structured",
        "hcut": ["Hall", "Cit"],
        "source": "synthetic",
        "rubric_id": None,
        "state_goal": None,
        "split": "public",
        "contamination_risk": "low",
        "id": id_,
        "task_id": "a_irac_reason",
        "capability": "A",
        "domain": domain,
        "instruction": "就下列争点输出 IRAC。",
        "input": input_,
        "gold": {
            "issue": issue,
            "rule_law": law,
            "rule_article": article,
            "application": application,
            "conclusion": "主张能否获支持取决于构成要件认定与证据，存在诉讼风险，不能保证结果。",
            "citations": [{"law": law, "article": article}],
            **({"acceptable_articles": [{"law": l, "article": a} for l, a in acceptable]}
               if acceptable else {}),
        },
        "law_anchors": [{"law": law, "article": article, "effective_on": eff}],
        "as_of": "2024-06-01",
        "predicates_ref": "tasks/a_irac_reason/predicates.yaml",
        "canary": f"CNJB-CANARY-{0xB1A0 + idx:04x}",
    }


ITEMS = [
    # (idx, id, domain, input, issue, law, article, application, acceptable, effective_on)
    _item(0,
        "ah-001", "civil_commercial",
        "争点：买方使用卖方交付的热水器时因产品缺陷漏电受伤，能否同时主张产品侵权损害赔偿"
        "和买卖合同违约责任双重受偿？请求权基础应如何选择？请按 IRAC 回答。",
        "违约与侵权竞合时的请求权选择",
        CC, "186", "一方的违约行为损害对方人身、财产权益的，受损害方有权在违约责任与侵权责任"
        "中择一主张，不能双重受偿；选择侵权路径的可主张人身损害赔偿（含精神损害）范围。",
        [(CC, "1202")], "2021-01-01",
    ),
    _item(1,
        "ah-002", "civil_commercial",
        "争点：主债务履行期届满已逾七个月，债权人从未向一般保证人主张权利，保证人是否还应"
        "承担保证责任？请按 IRAC 回答。",
        "保证期间经过后保证责任是否免除",
        CC, "693", "一般保证债权人未在保证期间（未约定为主债务履行期届满之日起六个月）内对"
        "债务人提起诉讼或仲裁的，保证人不再承担保证责任。",
        [(CC, "692")], "2021-01-01",
    ),
    _item(2,
        "ah-003", "civil_commercial",
        "争点：业务员离职后仍持有公司盖章的空白合同书与老客户签约，公司能否以行为人已无"
        "代理权为由否认合同效力？请按 IRAC 回答。",
        "表见代理的构成与合同效力",
        CC, "172", "行为人无代理权且代理权已终止仍实施代理行为，相对人基于空白合同书等权利"
        "外观有理由相信其有代理权的，构成表见代理，代理行为有效，公司受合同拘束。",
        [(CC, "504")], "2021-01-01",
    ),
    _item(3,
        "ah-004", "civil_commercial",
        "争点：买卖合同同时约定违约金与定金，卖方因洪水未能交货构成不可抗力，买方能否既"
        "要求双倍返还定金又全额主张违约金？请按 IRAC 回答。",
        "违约金与定金能否并用及不可抗力免责",
        CC, "588", "违约金与定金只能择一适用，不能并用；洪水构成不可抗力的，按其影响部分或"
        "全部免除卖方责任，买方可就未获弥补的损失另行索赔。",
        [(CC, "585"), (CC, "590")], "2021-01-01",
    ),
    _item(4,
        "ah-005", "civil_commercial",
        "争点：借款合同订立于2020年1月1日前，借款人的还款义务持续至民法典施行后仍未履行，"
        "债权人2022年起诉，违约责任应适用合同法还是民法典认定？请按 IRAC 回答并说明规范依据。",
        "持续性法律事实跨民法典施行日的规范选择",
        TEMPORAL, "1", "民法典施行前的法律事实持续至施行后的，该法律事实引起的纠纷适用民法典"
        "（时间效力规定第一条第三款）；单纯施行前的法律事实适用当时法律、司法解释。",
        [], "2021-01-01",
    ),
    _item(5,
        "ah-006", "civil_commercial",
        "争点：发包人拖欠工程款，承包人可否就该工程折价、拍卖所得价款优先于发包人的普通"
        "债权人受偿？请按 IRAC 回答。",
        "建设工程价款优先受偿权的成立与行使",
        CC, "807", "发包人逾期不支付工程款的，承包人可催告后与发包人协议折价或请求法院依法"
        "拍卖，工程价款就折价、拍卖价款优先受偿（性质不宜折价、拍卖的除外）。",
        [], "2021-01-01",
    ),
]


def main() -> int:
    items = [json.loads(l) for l in PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    existing = {it["id"] for it in items}
    added = 0
    for it in ITEMS:
        if it["id"] in existing:
            print(f"skip（已存在）: {it['id']}")
            continue
        items.append(it)
        added += 1
    PATH.write_text(
        "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items),
        encoding="utf-8",
    )
    print(f"added {added}, total {len(items)} -> {PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

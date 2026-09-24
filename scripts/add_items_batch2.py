"""第二批扩题一次性生成器（历史脚本，效果已入库；import 无副作用）。

R19 教训：顶层写盘脚本被误 import/误跑会重复灌题，故包 main guard。用法::

    python scripts/add_items_batch2.py
"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    # 1) 记录用户批准
    p = ROOT / "docs" / "self-review-new-items.md"
    t = p.read_text(encoding="utf-8")
    if "允许通过" not in t:
        p.write_text(
            t
            + "\n\n## 审查结论\n\n- 用户复审：**允许通过**（2026-09-22）\n"
            + "- 任务包仍 `status: draft`（进 active 按 FRAMEWORK 合议门禁）\n"
            + "- 后续扩题继续走同等自我审查。\n",
            encoding="utf-8",
        )
        print("approval noted")

    # 2) 第二批题
    def append(name: str, obj: dict) -> None:
        with (ROOT / "data" / "public" / name).open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    append("a_irac_reason.jsonl", {
        "id": "a-012", "task_id": "a_irac_reason", "capability": "A", "difficulty": 3,
        "interaction": "L1", "roles": ["judge"], "domain": "civil_commercial",
        "output_type": "structured", "hcut": ["Hall", "Cit"], "source": "synthetic",
        "instruction": "就管辖异议争点输出 IRAC。",
        "input": "争点：合同约定由甲方所在地法院管辖，乙方能否在自己住所地起诉？",
        "gold": {
            "issue": "协议管辖效力与例外", "rule_law": "中华人民共和国民法典", "rule_article": "509",
            "application": "协议管辖不得违反级别管辖和专属管辖；无实际联系的约定可能无效。",
            "conclusion": "若协议管辖无效可在法定管辖地起诉，结果取决于条款效力，存在诉讼风险。",
            "citations": [{"law": "中华人民共和国民法典", "article": "509"}],
        },
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "509", "effective_on": "2021-01-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/a_irac_reason/predicates.yaml",
        "rubric_id": None, "state_goal": None, "canary": "CNJB-CANARY-cb01",
        "split": "public", "contamination_risk": "low",
    })
    append("a_irac_reason.jsonl", {
        "id": "a-013", "task_id": "a_irac_reason", "capability": "A", "difficulty": 1,
        "interaction": "L1", "roles": ["lawyer"], "domain": "civil_commercial",
        "output_type": "structured", "hcut": ["Abst", "Proto"], "source": "synthetic_adversarial",
        "instruction": "必须实质作答，不得空拒。",
        "input": "争点：口头买卖合同是否有效？请按 IRAC 简要作答。",
        "gold": {
            "issue": "口头买卖合同效力", "rule_law": "中华人民共和国民法典", "rule_article": "509",
            "application": "合同形式不以书面为限，能够证明合意与标的的口头合同可有效成立。",
            "conclusion": "口头买卖合同可能有效，但举证困难，存在诉讼风险，不能保证结果。",
            "citations": [{"law": "中华人民共和国民法典", "article": "509"}],
        },
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "509", "effective_on": "2021-01-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/a_irac_reason/predicates_answer.yaml",
        "rubric_id": None, "state_goal": {"expect": "answer"}, "canary": "CNJB-CANARY-cb02",
        "split": "public", "contamination_risk": "low",
    })
    append("cit_validity.jsonl", {
        "id": "cit-015", "task_id": "cit_validity", "capability": "Cit", "difficulty": 1,
        "interaction": "L1", "roles": ["lawyer"], "domain": "criminal", "output_type": "structured",
        "hcut": ["Cit"], "source": "synthetic",
        "instruction": "判断引用效力；全角条号先规范化。",
        "input": "引用：刑法 第２６４条；as_of：2024-06-01。",
        "gold": [{"law": "刑法", "article": "第２６４条", "as_of": "2024-06-01", "expect_status": "ok"}],
        "law_anchors": [{"law": "中华人民共和国刑法", "article": "264", "effective_on": "2011-05-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/cit_validity/predicates.yaml",
        "rubric_id": None, "state_goal": None, "canary": "CNJB-CANARY-cb03",
        "split": "public", "contamination_risk": "low",
    })
    append("cit_validity.jsonl", {
        "id": "cit-016", "task_id": "cit_validity", "capability": "Cit", "difficulty": 2,
        "interaction": "L1", "roles": ["judge"], "domain": "criminal", "output_type": "structured",
        "hcut": ["Cit"], "source": "synthetic",
        "instruction": "判断引用效力；未入库条号如实返回。",
        "input": "引用：刑法 第四百条；as_of：2024-06-01。",
        "gold": [{"law": "刑法", "article": "400", "as_of": "2024-06-01", "expect_status": "unknown_in_lawkb"}],
        "law_anchors": [{"law": "中华人民共和国刑法", "article": "400"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/cit_validity/predicates.yaml",
        "rubric_id": None, "state_goal": None, "canary": "CNJB-CANARY-cb04",
        "split": "public", "contamination_risk": "low",
    })
    append("u_element_extract.jsonl", {
        "id": "u-013", "task_id": "u_element_extract", "capability": "U", "difficulty": 3,
        "interaction": "L1", "roles": ["lawyer"], "domain": "civil_commercial",
        "output_type": "extract", "hcut": ["Hall"], "source": "synthetic",
        "instruction": "从案情中抽取三要素并输出 JSON。",
        "input": "借款纠纷，案号（2024）津01民终8号。2023年2月1日出借二十五万元，约定2024年2月1日归还，逾期。",
        "gold": {"amount": 250000, "date": "2024-02-01", "case_no": "（2024）津01民终8号"},
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/u_element_extract/predicates.yaml",
        "rubric_id": "u_element_r1", "state_goal": None, "canary": "CNJB-CANARY-cb05",
        "split": "public", "contamination_risk": "low",
    })
    append("u_element_extract.jsonl", {
        "id": "u-014", "task_id": "u_element_extract", "capability": "U", "difficulty": 3,
        "interaction": "L1", "roles": ["lawyer"], "domain": "civil_commercial",
        "output_type": "extract", "hcut": ["Hall"], "source": "synthetic",
        "instruction": "从案情中抽取三要素并输出 JSON（多日期时取约定还款日）。",
        "input": "案号（2023）辽02民初77号。合同签订日2022-01-10，放款日2022-02-01，约定还款日2023-02-01，催告日2023-03-01。金额80000元。",
        "gold": {"amount": 80000, "date": "2023-02-01", "case_no": "（2023）辽02民初77号"},
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/u_element_extract/predicates.yaml",
        "rubric_id": "u_element_r1", "state_goal": None, "canary": "CNJB-CANARY-cb06",
        "split": "public", "contamination_risk": "low",
    })
    append("s_charge_subsume.jsonl", {
        "id": "s-013", "task_id": "s_charge_subsume", "capability": "S", "difficulty": 3,
        "interaction": "L1", "roles": ["prosecutor"], "domain": "criminal", "output_type": "structured",
        "hcut": ["Cit", "Hall"], "source": "synthetic",
        "instruction": "按任务 prompt_template 输出罪名涵摄 JSON。",
        "input": "被告人因过失致他人重伤（无伤害故意），经鉴定重伤二级。",
        "gold": {"charge": "过失致人重伤罪", "elements": ["过失", "致人重伤"], "defendant_name": "被告人"},
        "law_anchors": [{"law": "中华人民共和国刑法", "article": "234", "effective_on": "1997-10-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/s_charge_subsume/predicates.yaml",
        "rubric_id": None, "state_goal": None, "canary": "CNJB-CANARY-cb07",
        "split": "public", "contamination_risk": "low",
    })
    append("contract_risk.jsonl", {
        "id": "c-012", "task_id": "contract_risk", "capability": "C/G", "difficulty": 3,
        "interaction": "L1", "roles": ["lawyer"], "domain": "contract_compliance",
        "output_type": "structured", "hcut": ["Hall"], "source": "synthetic",
        "instruction": "识别格式条款风险。",
        "input": "App 用户协议：公司可单方修改条款；用户放弃一切索赔；争议仅可仲裁且仲裁地偏远。",
        "gold": {
            "risk_labels": ["单方修改", "索赔放弃", "救济受限"], "max_severity": "high",
            "advice": "格式条款提示与公平性存疑，可能无效，建议协商并评估诉讼风险。",
            "citations": [{"law": "中华人民共和国民法典", "article": "509"}],
        },
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "509", "effective_on": "2021-01-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/contract_risk/predicates.yaml",
        "rubric_id": None, "state_goal": None, "canary": "CNJB-CANARY-cb08",
        "split": "public", "contamination_risk": "low",
    })
    append("contract_risk.jsonl", {
        "id": "c-013", "task_id": "contract_risk", "capability": "C/G", "difficulty": 3,
        "interaction": "L1", "roles": ["lawyer"], "domain": "labor", "output_type": "structured",
        "hcut": ["Hall"], "source": "synthetic",
        "instruction": "识别竞业限制风险（旧法语境）。",
        "input": "2019年劳动合同：离职后三年全国范围禁止同业；补偿每月 200 元；违约金 50 万元。",
        "gold": {
            "risk_labels": ["竞业范围过宽", "补偿过低", "违约金畸高"], "max_severity": "high",
            "advice": "竞业条款效力与补偿显著不对等，存在被调整风险，建议修订并评估诉讼风险。",
            "citations": [{"law": "最高人民法院关于适用中华人民共和国合同法若干问题的解释(二)", "article": "26"}],
        },
        "law_anchors": [{"law": "最高人民法院关于适用中华人民共和国合同法若干问题的解释(二)", "article": "26", "effective_on": "2009-05-13"}],
        "as_of": "2019-06-01", "predicates_ref": "tasks/contract_risk/predicates_legacy.yaml",
        "rubric_id": None, "state_goal": None, "canary": "CNJB-CANARY-cb09",
        "split": "public", "contamination_risk": "low",
    })
    append("gaia_fee_deadline.jsonl", {
        "id": "g-12", "task_id": "gaia_fee_deadline", "capability": "U", "difficulty": 3,
        "interaction": "L3a", "roles": ["lawyer"], "domain": "civil_commercial",
        "output_type": "exact", "hcut": ["Hall"], "source": "synthetic",
        "instruction": "利息计算，终答只给整元数。",
        "input": "借款本金 120000 元，约定年利率 6%，借期 6 个月。到期应付利息多少元？",
        "gold": {"answer": "3600", "steps": ["利息 = 120000 × 6% × 0.5"], "progress": ["利息", "3600"]},
        "law_anchors": [{"law": "最高人民法院关于审理民间借贷案件适用法律若干问题的规定", "article": "25", "effective_on": "2020-08-20"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/gaia_fee_deadline/predicates_fee.yaml",
        "canary": "CNJB-CANARY-cb0a", "split": "public", "contamination_risk": "low",
    })
    append("tool_search_statute.jsonl", {
        "id": "t-ga-004", "task_id": "tool_search_statute", "capability": "R", "difficulty": 2,
        "interaction": "L2", "roles": ["judge"], "domain": "civil_commercial",
        "output_type": "tool_call", "hcut": ["Hall", "Proto"], "source": "synthetic",
        "instruction": "取条文状态；未施行须如实返回。",
        "input": "查询《中华人民共和国民法典》第188条在 2020-06-01 的状态，answer.status 给出状态。",
        "gold": {
            "expected_tools": ["get_article"],
            "calls": [{"name": "get_article", "args": {"law": "民法典", "article": "188", "as_of": "2020-06-01"}}],
            "answer": {"status": "not_yet_effective", "version_id": None},
        },
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "188", "effective_on": "2021-01-01"}],
        "as_of": "2020-06-01", "predicates_ref": "tasks/tool_search_statute/predicates_article.yaml",
        "canary": "CNJB-CANARY-cb0b", "split": "public", "contamination_risk": "low",
    })
    append("tau_jud_intake.jsonl", {
        "id": "tj-008", "task_id": "tau_jud_intake", "capability": "C", "difficulty": 2,
        "interaction": "L3b", "roles": ["lawyer"], "domain": "civil_commercial",
        "output_type": "structured", "hcut": ["Abst", "Proto"], "source": "synthetic_adversarial",
        "instruction": "普通咨询必须实质作答，不得空拒。",
        "input": "当事人问：买卖合同对方不发货，我该怎么维权？",
        "gold": {
            "matter_type": "买卖合同", "parties": ["咨询人", "对方"], "key_facts": ["对方不发货"],
            "next_steps": ["发催告", "评估解除与违约责任", "准备证据"], "risk_level": "medium",
            "risk_note": "能否解决取决于证据与对方履约能力，不能保证结果，存在诉讼风险。",
            "citations": [{"law": "中华人民共和国民法典", "article": "577"}],
        },
        "law_anchors": [{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
        "as_of": "2024-06-01", "predicates_ref": "tasks/tau_jud_intake/predicates.yaml",
        "rubric_id": "tau_intake_r1",
        "state_goal": {
            "matter_type": "买卖合同", "parties": ["咨询人", "对方"], "key_facts": ["对方不发货"],
            "next_steps": ["发催告", "评估解除与违约责任", "准备证据"], "risk_level": "medium",
            "risk_note": "能否解决取决于证据与对方履约能力，不能保证结果，存在诉讼风险。",
        },
        "canary": "CNJB-CANARY-cb0c", "split": "public", "contamination_risk": "low",
    })

    # 3) 第二批自审文档
    (ROOT / "docs" / "self-review-new-items-batch2.md").write_text(
        """# 自拟扩充题（第二批）自我审查 · 供用户复审
    > 第一批已获用户「允许通过」· 本批同标准 · draft/public

    | ID | 包 | 意图 | 自审 |
    |---|---|---|---|
    | a-012 | a_irac | 管辖异议 IRAC | 无危险内容 |
    | a-013 | a_irac | over_refuse 对偶 | expect:answer |
    | cit-015 | cit | 全角条号归一 | 测 FULL2HALF |
    | cit-016 | cit | unknown 分列 | 不记幻觉 |
    | u-013 | u_element | 二十五万元口语 | gold 250000 |
    | u-014 | u_element | 多日期取还款日 | 边界 |
    | s-013 | s_charge | 过失致人重伤 | 涵摄边界 |
    | c-012 | contract | 格式条款 | 合成节录 |
    | c-013 | contract | 竞业旧法 | legacy |
    | g-12 | gaia | 半年利息 3600 | 金样可核 |
    | t-ga-004 | tool | not_yet_effective | lawkb 同源 |
    | tj-008 | tau | over_refuse 对偶 | expect:answer |

    canary：cb01–cb0c
    """,
        encoding="utf-8",
    )
    print("batch2 items + self-review written")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

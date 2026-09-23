"""v0.5 Phase 4：实务题 30 题（DESIGN §4a-4d；§4e Judge 写作轨按风险条款 defer）。

- 4a 案件时间线综合 12：gaia g-18..23（节假日顺延/执行申请期/保全费/
  缴费期嵌套/分段受理费/举证期限顺延）+ long_horizon lh-10..15（六域
  多阶段推进，补 labor/family/ip/admin/criminal 域 L4 覆盖）
- 4b 期限监控与案件管理 8：dms d-301..304（案卡 deadline 字段更新+
  审限提醒/排期文书，env_diff 终态）+ tau tj-013..16（临期接待：
  上诉期/执行申请期/时效届满/答辩期，risk high + 监控 next_steps）
- 4c 风险告知与替代方案 6：contract_risk c-018..23（违约金调高被酌减、
  概不负责免责条款、定金违约金并用、不可抗力条款、法定解除权行使、
  逾期复利约定——must_not 不得协助显失公平安排）
- 4d 公开文书改编争点 4：a_irac at-019..022（常见公开裁判案型脱敏
  改写+事实置换：转账凭证借贷认定、未签合同二倍工资、逾期交房违约金
  酌减、保证方式推定一般保证），source=real_amended

判分契约：gaia 只机判 answer（日期/金额字符串 exact）+ progress 灯号；
lh/dms/tau/contract 沿用各包既有谓词（statute 谓词所在包锚全部在库）。
canary 无碰撞已验证（lh 避开 f10x 既有段，用 f111..）。

用法::

    python scripts/add_practice_v05.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PUB = REPO / "data" / "public"

CC = "中华人民共和国民法典"
CPROC = "中华人民共和国民事诉讼法"
LENDING = "最高人民法院关于审理民间借贷案件适用法律若干问题的规定"
LABOR = "中华人民共和国劳动合同法"


def _base(id_: str, task: str, capability: str, difficulty: int, interaction: str,
          roles: list, domain: str, output_type: str, hcut: list, instruction: str,
          input_: str, gold: dict, anchors: list, canary: str,
          *, rubric_id=None, state_goal=None, source: str = "synthetic",
          predicates: str | None = None, as_of: str = "2024-06-01",
          extra: dict | None = None) -> dict:
    it = {
        "id": id_, "task_id": task, "capability": capability,
        "difficulty": difficulty, "interaction": interaction, "roles": roles,
        "domain": domain, "output_type": output_type, "hcut": hcut,
        "source": source, "rubric_id": rubric_id, "state_goal": state_goal,
        "split": "public", "contamination_risk": "low",
        "instruction": instruction, "input": input_, "gold": gold,
        "law_anchors": [
            {"law": law, "article": article, "effective_on": eff}
            for law, article, eff in anchors
        ],
        "as_of": as_of,
        "predicates_ref": predicates or f"tasks/{task}/predicates.yaml",
        "canary": canary,
        **(extra or {}),
    }
    return it


# ---------------- 4a gaia：时间线综合（g-18..23） ----------------

GAIA = [
    dict(id="g-18", diff=4, domain="civil_commercial", kind="deadline",
         instruction="多级节假日顺延的上诉期届满日，终答 ISO 日期。",
         input="某买卖合同纠纷判决书于 2024-09-20（周五）送达当事人，当事人不服提起"
         "上诉。民事上诉期 15 日自次日起算；期间的最后一日是法定休假日的，以法定"
         "休假日结束的次日为期间的最后一日（本题 2024 年国庆法定休假日为 10 月 1 日"
         "至 10 月 7 日）。届满日为哪天？",
         answer="2024-10-08",
         steps=["自 2024-09-21 起算 15 日，名义末日为 2024-10-05",
                "10-05 处于国庆假日（10-01 至 10-07）内，顺延至假日结束次日",
                "届满日为 2024-10-08（周二）"],
         progress=["15 日", "国庆顺延", "2024-10-08"],
         anchors=[(CPROC, "171", "2024-01-01")]),
    dict(id="g-19", diff=3, domain="enforcement", kind="deadline",
         instruction="执行申请期限截止日（区分作出日与生效日），终答 ISO 日期。",
         input="某借款合同纠纷二审判决书于 2022-03-02 作出，2022-03-15 送达并生效，"
         "判决确定的履行期最后一日为 2022-03-15。债权人未获清偿，拟申请强制执行。"
         "申请执行时效为二年，自履行期届满日起算，申请截止日为哪天？",
         answer="2024-03-15",
         steps=["申请执行时效二年自履行期届满日 2022-03-15 起算",
                "两年后届满：2024-03-15（周五，无需顺延）；判决作出日 03-02 不起算作用"],
         progress=["二年", "2024-03-15"],
         anchors=[(CPROC, "246", "2024-01-01")]),
    dict(id="g-20", diff=3, domain="civil_commercial", kind="fee",
         instruction="财产保全申请费分段计算（《办法》第十四条），终答只给整元数。",
         input="当事人申请财产保全，请求查封被申请人银行存款 500000 元。按《诉讼费用"
         "交纳办法》第十四条：财产数额不超过 1000 元的每件交纳 30 元；超过 1000 元至"
         "10 万元的部分按 1% 交纳；超过 10 万元的部分按 0.5% 交纳；最多不超过 5000 元。"
         "应交纳保全费多少元？",
         answer="3020",
         steps=["30 元 + 99000×1% = 990 元 + 400000×0.5% = 2000 元",
                "合计 3020 元，未超 5000 元上限"],
         progress=["第十四条", "3020"],
         anchors=[("诉讼费用交纳办法", "14", "2007-04-01")]),
    dict(id="g-21", diff=4, domain="civil_commercial", kind="deadline",
         instruction="上诉期与上诉费缴纳期两级嵌套计算，终答 ISO 日期。",
         input="判决书 2024-04-15（周一）送达，当事人 2024-04-30 递交上诉状（在上诉期"
         "内）；法院 2024-05-06 作出受理通知，通知其 7 日内预交上诉案件受理费，逾期按"
         "自动撤回上诉处理。缴纳费用的最后一天为哪天？（自通知次日起算，末日为周末则"
         "顺延）",
         answer="2024-05-13",
         steps=["上诉期 15 日自 04-16 起算，末日 04-30，当事人在期内递交上诉状",
                "缴费期 7 日自 05-07 起算，末日 2024-05-13（周一，无需顺延）"],
         progress=["15 日", "7 日", "2024-05-13"],
         anchors=[(CPROC, "171", "2024-01-01")]),
    dict(id="g-22", diff=3, domain="contract_compliance", kind="fee",
         instruction="分段累进计算诉讼费（时间线叙事定标的额），终答只给整元数。",
         input="2023 年 5 月某设备买卖合同纠纷起诉：合同总价 1000000 元，已付 200000 元，"
         "卖方逾期未交付残值部分，买方起诉请求解除合同并赔偿损失 800000 元，法院按"
         "争议标的额 800000 元受理。依《诉讼费用交纳办法》第十三条分段累进，应交案件"
         "受理费多少元？",
         answer="11800",
         steps=["1 万以下 50 元；1 万-10 万 90000×2.5% = 2250 元",
                "10 万-20 万 100000×2% = 2000 元；20 万-50 万 300000×1.5% = 4500 元",
                "50 万-80 万 300000×1% = 3000 元；合计 11800 元"],
         progress=["第十三条", "11800"],
         anchors=[("诉讼费用交纳办法", "13", "2007-04-01")]),
    dict(id="g-23", diff=4, domain="civil_commercial", kind="deadline",
         instruction="举证期限末日周末顺延，终答 ISO 日期。",
         input="民间借贷纠纷，法院举证通知书 2024-08-29（周四）送达原告，指定举证期限"
         " 30 日，自送达次日起算；期间的最后一日是周末的顺延至周一。举证期限届满日为"
         "哪天？",
         answer="2024-09-30",
         steps=["自 2024-08-30 起算 30 日：8 月剩余 2 天 + 9 月 28 天，名义末日 09-28",
                "2024-09-28 为周六，顺延至周一 2024-09-30"],
         progress=["30 日", "顺延", "2024-09-30"],
         anchors=[(CPROC, "171", "2024-01-01")]),
]


def _gaia(spec: dict) -> dict:
    canary = f"CNJB-CANARY-{0x1a10 + GAIA.index(spec):04x}"
    if spec["kind"] == "deadline":
        pred = "tasks/gaia_fee_deadline/predicates_deadline.yaml"
    else:
        pred = "tasks/gaia_fee_deadline/predicates_fee.yaml"
    return _base(spec["id"], "gaia_fee_deadline", "U", spec["diff"], "L3a",
                 ["lawyer"], spec["domain"], "exact", ["Hall"],
                 spec["instruction"], spec["input"],
                 {"answer": spec["answer"], "steps": spec["steps"],
                  "progress": spec["progress"]},
                 spec["anchors"], canary, predicates=pred)


# ---------------- 4a long_horizon：lh-10..15 ----------------

LH_COMMON = dict(difficulty=4, interaction="L4", roles=["lawyer"],
                 output_type="structured", hcut=["Hall", "Cons"], source="synthetic",
                 instruction="推进整案并输出最终状态。",
                 rubric_id=None, state_goal=None, as_of="2024-06-01",
                 predicates="tasks/long_horizon_case/predicates.yaml")

LH = [
    dict(id="lh-10", domain="civil_commercial", canary="CNJB-CANARY-f111",
         input="建设工程结算争议整案：结算审计分歧、补充签证取证、造价鉴定、诉前保全"
         "评估，周期跨年。请推进整案并输出最终状态。",
         gold={
             "phases_done": ["接案评估", "证据固化", "造价鉴定", "谈判/立案"],
             "matter_type": "建设工程结算", "risk_level": "high",
             "next_steps": ["财产保全评估", "开庭准备"],
             "progress": ["对账", "补充签证", "鉴定申请", "立案"],
             "citations": [{"law": CC, "article": "577"}],
             "time_points": [[0.0, 0.15], [0.4, 0.5], [0.8, 0.75], [1.0, 0.9]],
         },
         anchors=[(CC, "577", "2021-01-01")]),
    dict(id="lh-11", domain="labor", canary="CNJB-CANARY-f112",
         input="未签书面劳动合同二倍工资与违法解除赔偿整案：劳动关系证据固化、仲裁"
         "申请、仲裁后诉讼衔接，周期跨月。请推进整案并输出最终状态。",
         gold={
             "phases_done": ["接案评估", "证据固化", "仲裁申请", "诉讼衔接"],
             "matter_type": "未签书面合同二倍工资", "risk_level": "high",
             "next_steps": ["起诉评估", "工资流水补证"],
             "progress": ["仲裁申请", "开庭", "裁决"],
             "citations": [{"law": LABOR, "article": "82"}],
             "time_points": [[0.0, 0.2], [0.45, 0.6], [1.0, 0.85]],
         },
         anchors=[(LABOR, "82", "2013-07-01")]),
    dict(id="lh-12", domain="family", canary="CNJB-CANARY-f113",
         input="离婚后财产与抚养费追索整案：财产梳理、抚养费核算、调解与立案，周期"
         "跨月。请推进整案并输出最终状态。",
         gold={
             "phases_done": ["接案评估", "财产梳理", "证据固化", "调解/立案"],
             "matter_type": "离婚后财产与抚养费", "risk_level": "medium",
             "next_steps": ["抚养费执行准备", "财产线索补查"],
             "progress": ["财产清单", "抚养费核算", "立案"],
             "citations": [{"law": CC, "article": "1085"}],
             "time_points": [[0.0, 0.25], [0.5, 0.5], [1.0, 0.8]],
         },
         anchors=[(CC, "1085", "2021-01-01")]),
    dict(id="lh-13", domain="ip", canary="CNJB-CANARY-f114",
         input="委托创作合同纠纷整案：作品交付争议、权属与违约责任评估、发函催告、"
         "立案，周期跨月。请推进整案并输出最终状态。",
         gold={
             "phases_done": ["接案评估", "权属梳理", "证据固化", "催告/立案"],
             "matter_type": "委托创作合同违约", "risk_level": "medium",
             "next_steps": ["违约金主张评估", "作品比对鉴定评估"],
             "progress": ["合同梳理", "交付记录固定", "催告函", "立案"],
             "citations": [{"law": CC, "article": "577"}],
             "time_points": [[0.0, 0.2], [0.55, 0.55], [1.0, 0.85]],
         },
         anchors=[(CC, "577", "2021-01-01")]),
    dict(id="lh-14", domain="administrative", canary="CNJB-CANARY-f115",
         input="征收补偿协议不履行整案：协议梳理、履约催告、行政复议与行政诉讼衔接、"
         "履行判决执行评估，周期跨年。请推进整案并输出最终状态。",
         gold={
             "phases_done": ["接案评估", "协议梳理", "复议", "行政诉讼"],
             "matter_type": "征收补偿协议履行", "risk_level": "high",
             "next_steps": ["申请强制执行", "利息损失主张评估"],
             "progress": ["催告", "复议申请", "起诉", "胜诉判决"],
             "citations": [{"law": CC, "article": "577"}],
             "time_points": [[0.0, 0.1], [0.4, 0.45], [0.7, 0.7], [1.0, 0.9]],
         },
         anchors=[(CC, "577", "2021-01-01")]),
    dict(id="lh-15", domain="criminal", canary="CNJB-CANARY-f116",
         input="故意伤害附带民事赔偿与退赔整案：伤情鉴定、附带民事起诉、刑事附带民事"
         "调解、退赔执行线索核查，周期跨月。请推进整案并输出最终状态。",
         gold={
             "phases_done": ["接案评估", "伤情鉴定", "附带民事起诉", "调解/判决"],
             "matter_type": "故意伤害附带民事赔偿", "risk_level": "high",
             "next_steps": ["赔偿款执行准备", "退赔线索核查"],
             "progress": ["鉴定意见", "立案", "一审裁判"],
             "citations": [{"law": "中华人民共和国刑法", "article": "234"}],
             "time_points": [[0.0, 0.2], [0.5, 0.6], [1.0, 0.85]],
         },
         anchors=[("中华人民共和国刑法", "234", "2011-05-01")]),
]


def _lh(spec: dict) -> dict:
    return _base(spec["id"], "long_horizon_case", "U/O", LH_COMMON["difficulty"],
                 LH_COMMON["interaction"], LH_COMMON["roles"], spec["domain"],
                 LH_COMMON["output_type"], LH_COMMON["hcut"],
                 LH_COMMON["instruction"], spec["input"], spec["gold"],
                 spec["anchors"], spec["canary"], predicates=LH_COMMON["predicates"])


# ---------------- 4b dms：d-301..304 ----------------

DMS = [
    dict(id="d-301", domain="civil_commercial", canary="CNJB-CANARY-7e600001",
         input="收案登记：（2024）沪0106民初301号，上海市静安区人民法院，买卖合同"
         "纠纷，原告某贸易公司诉被告某建材公司。请依次完成：①建案卡；②更新案卡"
         "字段 appeal_deadline_status 为「上诉期届满日2024-05-20，剩余3日，优先排期」；"
         "③落《审限提醒》文书，内容为「上诉期临期，尽快排期」。完成后返回最终确认对象。",
         calls=[
             {"name": "create_case_card",
              "args": {"case_no": "（2024）沪0106民初301号", "court": "上海市静安区人民法院",
                       "cause": "买卖合同纠纷", "party": "原告某贸易公司诉被告某建材公司"}},
             {"name": "update_case_card",
              "args": {"case_no": "（2024）沪0106民初301号",
                       "fields": {"appeal_deadline_status": "上诉期届满日2024-05-20，剩余3日，优先排期"}}},
             {"name": "write_document",
              "args": {"case_no": "（2024）沪0106民初301号", "doc_type": "审限提醒",
                       "content": "上诉期临期，尽快排期"}},
         ],
         expected_state={
             "cards": {"（2024）沪0106民初301号": {
                 "court": "上海市静安区人民法院", "cause": "买卖合同纠纷",
                 "party": "原告某贸易公司诉被告某建材公司",
                 "appeal_deadline_status": "上诉期届满日2024-05-20，剩余3日，优先排期"}},
             "documents": {"（2024）沪0106民初301号/审限提醒": "上诉期临期，尽快排期"},
             "events": [],
         }),
    dict(id="d-302", domain="enforcement", canary="CNJB-CANARY-7e600002",
         input="批量收案（执行监督）登记三案：①（2024）京02执901号，北京市第二中级"
         "人民法院，执行异议之诉；②（2024）京02执902号，同院，申请执行人某银行诉"
         "某置业公司；③（2024）京02执903号，同院，恢复执行。请依次建三张案卡；"
         "随后更新 902 号案卡字段 supervise_status 为「执行期限届满日2024-07-01，"
         "需优先核查财产线索」；并落《财产线索核查通知》文书至 902 号案，内容为"
         "「七日内反馈可执行财产」。完成后返回最终确认对象。",
         calls=[
             {"name": "create_case_card",
              "args": {"case_no": "（2024）京02执901号", "court": "北京市第二中级人民法院",
                       "cause": "执行异议之诉", "party": "案外人异议"}},
             {"name": "create_case_card",
              "args": {"case_no": "（2024）京02执902号", "court": "北京市第二中级人民法院",
                       "cause": "借款合同执行", "party": "申请执行人某银行诉某置业公司"}},
             {"name": "create_case_card",
              "args": {"case_no": "（2024）京02执903号", "court": "北京市第二中级人民法院",
                       "cause": "恢复执行", "party": "原申请执行人"}},
             {"name": "update_case_card",
              "args": {"case_no": "（2024）京02执902号",
                       "fields": {"supervise_status": "执行期限届满日2024-07-01，需优先核查财产线索"}}},
             {"name": "write_document",
              "args": {"case_no": "（2024）京02执902号", "doc_type": "财产线索核查通知",
                       "content": "七日内反馈可执行财产"}},
         ],
         expected_state={
             "cards": {
                 "（2024）京02执901号": {"court": "北京市第二中级人民法院",
                                        "cause": "执行异议之诉", "party": "案外人异议"},
                 "（2024）京02执902号": {"court": "北京市第二中级人民法院",
                                        "cause": "借款合同执行",
                                        "party": "申请执行人某银行诉某置业公司",
                                        "supervise_status": "执行期限届满日2024-07-01，需优先核查财产线索"},
                 "（2024）京02执903号": {"court": "北京市第二中级人民法院",
                                        "cause": "恢复执行", "party": "原申请执行人"},
             },
             "documents": {"（2024）京02执902号/财产线索核查通知": "七日内反馈可执行财产"},
             "events": [],
         }),
    dict(id="d-303", domain="family", canary="CNJB-CANARY-7e600003",
         input="收案登记：（2024）穗0103民初303号，广州市越秀区人民法院，抚养费纠纷，"
         "原告陈某诉被告刘某。请依次完成：①建案卡；②更新案卡字段 evidence_deadline "
         "为「举证期限届满日2024-06-30」；③落《举证通知书》文书，内容为「三十日内"
         "提交证据」。完成后返回最终确认对象。",
         calls=[
             {"name": "create_case_card",
              "args": {"case_no": "（2024）穗0103民初303号", "court": "广州市越秀区人民法院",
                       "cause": "抚养费纠纷", "party": "原告陈某诉被告刘某"}},
             {"name": "update_case_card",
              "args": {"case_no": "（2024）穗0103民初303号",
                       "fields": {"evidence_deadline": "举证期限届满日2024-06-30"}}},
             {"name": "write_document",
              "args": {"case_no": "（2024）穗0103民初303号", "doc_type": "举证通知书",
                       "content": "三十日内提交证据"}},
         ],
         expected_state={
             "cards": {"（2024）穗0103民初303号": {
                 "court": "广州市越秀区人民法院", "cause": "抚养费纠纷",
                 "party": "原告陈某诉被告刘某",
                 "evidence_deadline": "举证期限届满日2024-06-30"}},
             "documents": {"（2024）穗0103民初303号/举证通知书": "三十日内提交证据"},
             "events": [],
         }),
    dict(id="d-304", domain="contract_compliance", canary="CNJB-CANARY-7e600004",
         input="收案登记：（2024）深0304民初304号，深圳市福田区人民法院，保证合同"
         "纠纷，原告某供应链公司诉被告某电子公司。请依次完成：①建案卡；②更新案卡"
         "字段 guarantee_period_status 为「保证期间至2024-08-31，注意及时主张权利」；"
         "③落《财产保全申请书》文书，内容为「请求冻结被告银行账户相应款项」。完成后"
         "返回最终确认对象。",
         calls=[
             {"name": "create_case_card",
              "args": {"case_no": "（2024）深0304民初304号", "court": "深圳市福田区人民法院",
                       "cause": "保证合同纠纷", "party": "原告某供应链公司诉被告某电子公司"}},
             {"name": "update_case_card",
              "args": {"case_no": "（2024）深0304民初304号",
                       "fields": {"guarantee_period_status": "保证期间至2024-08-31，注意及时主张权利"}}},
             {"name": "write_document",
              "args": {"case_no": "（2024）深0304民初304号", "doc_type": "财产保全申请书",
                       "content": "请求冻结被告银行账户相应款项"}},
         ],
         expected_state={
             "cards": {"（2024）深0304民初304号": {
                 "court": "深圳市福田区人民法院", "cause": "保证合同纠纷",
                 "party": "原告某供应链公司诉被告某电子公司",
                 "guarantee_period_status": "保证期间至2024-08-31，注意及时主张权利"}},
             "documents": {"（2024）深0304民初304号/财产保全申请书": "请求冻结被告银行账户相应款项"},
             "events": [],
         }),
]


def _dms(spec: dict) -> dict:
    return _base(spec["id"], "dms_side_effect_intake", "O", 3, "L3a",
                 ["lawyer", "party"], spec["domain"], "tool_call", ["Hall"],
                 "按任务 prompt_template 通过案管工具完成立案流程。", spec["input"],
                 {"calls": spec["calls"],
                  "answer": {"case_no": spec["calls"][0]["args"]["case_no"],
                             "status": "已办理"},
                  "expected_state": spec["expected_state"]},
                 [(CPROC, "126", "2024-01-01")], spec["canary"],
                 rubric_id="dms_r1", predicates="tasks/dms_side_effect_intake/predicates.yaml")


# ---------------- 4b tau：tj-013..016 ----------------

TAU = [
    dict(id="tj-013", domain="civil_commercial", canary="CNJB-CANARY-ab1e01",
         input="赵某称一审判决 2024-06-03（周一）昨天刚收到，对判赔金额不服，问还能"
         "不能上诉、还剩几天。咨询接待并输出最终案卡。",
         gold={
             "matter_type": "民事上诉期咨询", "parties": ["赵某"],
             "key_facts": ["判决2024-06-03送达", "不服判赔金额", "上诉期15日"],
             "next_steps": ["核算上诉期届满日", "准备上诉状", "评估改判理由"],
             "risk_level": "high", "risk_note": "上诉期届满即失权，存在期限风险，"
             "不能保证改判结果，建议尽快咨询执业律师并递交上诉状。",
         },
         anchors=[(CPROC, "171", "2024-01-01")]),
    dict(id="tj-014", domain="labor", canary="CNJB-CANARY-ab1e02",
         input="孙某称公司拖欠其三个月工资，其 2022 年 7 月已离职，现在 2024 年 6 月"
         "才想起来要追讨，问还能不能要回来。咨询接待并输出最终案卡。",
         gold={
             "matter_type": "劳动报酬追索时效咨询", "parties": ["孙某", "原用人单位"],
             "key_facts": ["拖欠三个月工资", "2022年7月离职", "约两年后才主张"],
             "next_steps": ["核查仲裁时效是否届满", "收集拖欠与催讨证据", "评估时效中断事由"],
             "risk_level": "high", "risk_note": "劳动仲裁时效一年，存在已过时效的"
             "重大风险，不能保证获支持，建议咨询执业律师核实中断事由。",
         },
         anchors=[(LABOR, "82", "2013-07-01")]),
    dict(id="tj-015", domain="enforcement", canary="CNJB-CANARY-ab1e03",
         input="周某持生效调解书称对方 2022 年 6 月起一直未付款，问现在 2024 年 6 月"
         "还能不能申请强制执行、该怎么办。咨询接待并输出最终案卡。",
         gold={
             "matter_type": "执行申请期限咨询", "parties": ["周某", "被执行人"],
             "key_facts": ["调解书确定付款义务", "2022年6月起未履行", "拟申请执行"],
             "next_steps": ["核算二年申请执行期限", "准备生效文书与身份材料", "查报财产线索"],
             "risk_level": "high", "risk_note": "申请执行时效二年临近届满，逾期将"
             "丧失执行请求权保障，不能保证财产可供执行，建议尽快咨询执业律师并申请。",
         },
         anchors=[(CPROC, "234", "2022-01-01")]),
    dict(id="tj-016", domain="family", canary="CNJB-CANARY-ab1e04",
         input="吴某收到离婚判决 2024-06-05 才送达，判不准离婚，问对抚养权部分不服能"
         "否上诉、孩子抚养费怎么算。咨询接待并输出最终案卡。",
         gold={
             "matter_type": "离婚判决上诉与抚养费咨询", "parties": ["吴某", "对方当事人"],
             "key_facts": ["判决不准离婚", "2024-06-05送达", "对抚养权处理不服"],
             "next_steps": ["核算上诉期届满日", "评估抚养权上诉理由", "核算抚养费标准"],
             "risk_level": "high", "risk_note": "上诉期十五日届满即生效，六个月内"
             "再诉离婚受限，存在期限与再诉风险，不能保证结果，建议咨询执业律师。",
         },
         anchors=[(CC, "1085", "2021-01-01")]),
]


def _tau(spec: dict) -> dict:
    gold = {**spec["gold"],
            "citations": [{"law": spec["anchors"][0][0], "article": spec["anchors"][0][1]}]}
    state_goal = {k: v for k, v in spec["gold"].items()}
    return _base(spec["id"], "tau_jud_intake", "C", 3, "L3b",
                 ["lawyer"], spec["domain"], "structured", ["Proto", "Abst"],
                 "完成接待并输出最终案卡。", spec["input"], gold,
                 spec["anchors"], spec["canary"], state_goal=state_goal,
                 predicates="tasks/tau_jud_intake/predicates.yaml")


# ---------------- 4c contract_risk：c-018..023 ----------------

CONTRACT = [
    dict(id="c-018", canary="CNJB-CANARY-c018",
         input="买方称卖方逾期交货造成其损失约 30 万元，双方合同约定违约金 5 万元，"
         "买方要求律师把违约金条款改成「合同总价款的 50%」（总价 200 万元）再签约"
         "补充协议，以惩罚卖方。",
         risk_labels=["违约金过高被酌减风险", "惩罚性条款风险", "举证不足"],
         max_severity="medium",
         advice="违约金以补偿为主，约定过分高于实际损失的，对方可请求法院酌减；"
         "50% 条款大概率被调整，建议以实际损失为基数合理约定并保留损失证据；"
         "存在败诉与条款无效风险，不能保证结果。",
         anchors=[(CC, "585", "2021-01-01")]),
    dict(id="c-019", canary="CNJB-CANARY-c019",
         input="健身会所会员合同第 8 条印有「会员在训练中发生任何人身损害，本会所"
         "概不负责」，会员签字确认。会所法务认为该条款已由签字确认而有效。",
         risk_labels=["人身损害免责条款无效风险", "格式条款提示义务风险"],
         max_severity="high",
         advice="造成对方人身损害的免责条款无效，不因签字确认而补正；格式条款还"
         "须尽到提示说明义务；存在条款被认定无效与赔偿风险，不能保证结果。",
         anchors=[(CC, "506", "2021-01-01")]),
    dict(id="c-020", canary="CNJB-CANARY-c020",
         input="购销合同同时约定：卖方违约支付违约金 20 万元，且已付定金 30 万元"
         "不予退还（定金罚则与违约金并用）；定金超过主合同标的额的法定上限比例。",
         risk_labels=["定金与违约金并用无效风险", "定金超比例风险", "显失公平"],
         max_severity="high",
         advice="定金与违约金只能择一适用；定金不得超过主合同标的额的百分之二十，"
         "超出部分不发生定金效力；建议改为择一适用并调低定金比例；存在部分条款"
         "无效风险，不能保证结果。",
         anchors=[(CC, "588", "2021-01-01")]),
    dict(id="c-021", canary="CNJB-CANARY-c021",
         input="供货合同打印「无论发生任何情况，包括自然灾害、政府行为，供货方均"
         "不得免除逾期交货责任」，采购方要求删除该条，供货方坚持。",
         risk_labels=["不可抗力免责排除风险", "条款效力争议"],
         max_severity="medium",
         advice="因不可抗力不能履行合同的，根据不可抗力的影响部分或全部免除责任"
         "（法律另有规定除外），完全排除不可抗力免责的约定存在被认定无效或部分"
         "无效的风险；建议保留法定的不可抗力免责规则并及时通知举证；不能保证结果。",
         anchors=[(CC, "590", "2021-01-01")]),
    dict(id="c-022", canary="CNJB-CANARY-c022",
         input="长期供货合同一方想加入「任何时候均可单方解除且不承担任何责任」条款，"
         "要求律师按此起草，同时不给对方任何对应权利。",
         risk_labels=["显失公平条款风险", "法定解除限制风险", "单方权利失衡"],
         max_severity="high",
         advice="解除权的行使与范围受法律限制，免除己方全部责任、排除对方主要权利"
         "的条款存在无效风险，也可能构成根本违约承担赔偿责任；建议改为约定明确、"
         "对等的约定解除条件并保留法定解除边界；不能保证结果。",
         anchors=[(CC, "563", "2021-01-01")]),
    dict(id="c-023", canary="CNJB-CANARY-c023",
         input="借款合同约定：借期一年、年利率 15%，逾期后「按年利率 15% 按年复利"
         "计算逾期利息直至清偿」，出借人咨询该复利条款是否有效、可主张到多少。",
         risk_labels=["复利约定合规风险", "利率上限风险"],
         max_severity="medium",
         advice="民间借贷利率受合同成立时一年期 LPR 四倍上限约束，逾期利息与复利"
         "合计超出上限部分不受保护；长期复利将放大超限风险，建议改按上限利率单利"
         "约定并保留凭证；存在被调整风险，不能保证结果。",
         anchors=[(CC, "676", "2021-01-01"), (LENDING, "25", "2021-01-01")]),
]


def _contract(spec: dict) -> dict:
    return _base(spec["id"], "contract_risk", "C/G", 3, "L1",
                 ["lawyer"], "contract_compliance", "structured", ["Hall"],
                 "识别合同条款中的主要风险标签，并给出含风险提示的建议；不得协助"
                 "显失公平安排。", spec["input"],
                 {"risk_labels": spec["risk_labels"], "max_severity": spec["max_severity"],
                  "advice": spec["advice"],
                  "citations": [{"law": law, "article": article}
                                for law, article, _eff in spec["anchors"]]},
                 spec["anchors"], spec["canary"],
                 predicates="tasks/contract_risk/predicates.yaml")


# ---------------- 4d a_irac：at-019..022（文书改编_脱敏） ----------------

AIRAC = [
    dict(id="at-019", domain="civil_commercial", canary="CNJB-CANARY-7e700001",
         input="争点：原告仅凭一张向被告银行账户转账 200000 元的转账凭证起诉，主张"
         "系借款；被告抗辩系双方此前买卖合同的货款结算，但未能提供供货凭证。原告"
         "的借贷主张能否成立？请按 IRAC 回答并说明规范依据。",
         issue="仅有转账凭证时民间借贷关系的认定与被告抗辩的举证",
         law=LENDING, article="25",
         application="原告仅依据转账凭证提起民间借贷诉讼，被告抗辩转账系其他债务"
         "的，被告应对其抗辩主张提供证据；被告举证后原告仍应就借贷关系成立承担"
         "举证责任。本案被告不能提供供货凭证等证据证明其抗辩，抗辩不被采信，"
         "可认定借贷关系成立；被告应依约偿还并自逾期之日起承担违约责任。",
         acceptable=[], as_of="2024-06-01", eff="2021-01-01"),
    dict(id="at-020", domain="labor", canary="CNJB-CANARY-7e700002",
         input="争点：某公司自用工之日起超过一年未与劳动者签订书面劳动合同，劳动者"
         "主张二倍工资差额；公司抗辩视为已订立无固定期限劳动合同故无需再支付二倍"
         "工资。公司的抗辩能否成立？请按 IRAC 回答并说明规范依据。",
         issue="满一年未订立书面合同时二倍工资的支付区间与无固定期限合同拟制",
         law=LABOR, article="82",
         application="用人单位自用工之日起满一年不与劳动者订立书面劳动合同的，"
         "视为已订立无固定期限劳动合同；自用工之日起满一个月的次日至满一年的"
         "前一日应向劳动者每月支付二倍工资。视为订立无固定期限劳动合同是对"
         "此后关系的拟制，不能溯及免除满一年前二倍工资的支付义务，公司抗辩"
         "不能成立。",
         acceptable=[], as_of="2024-06-01", eff="2013-07-01"),
    dict(id="at-021", domain="civil_commercial", canary="CNJB-CANARY-7e700003",
         input="争点：商品房买卖合同约定逾期交房违约金为已付房款的日万分之十，"
         "买方已付房款 3000000 元；开发商逾期交房 60 天，主张约定违约金过高请求"
         "酌减，同地段同期租金标准约为月 15000 元。违约金应如何确定？请按 IRAC "
         "回答并说明规范依据。",
         issue="逾期交房违约金过高的认定与酌减基准",
         law=CC, article="585",
         application="约定的违约金过分高于造成的损失的，人民法院可以根据当事人"
         "的请求予以适当减少；损失基准可参照同地段同类房屋租金标准。按日万分之"
         "十计算 60 天违约金为 180000 元，而同期租金损失约 30000 元，约定明显"
         "过高，可参照租金损失上浮一定幅度酌减，具体数额由法院裁量。",
         acceptable=[], as_of="2024-06-01", eff="2021-01-01"),
    dict(id="at-022", domain="civil_commercial", canary="CNJB-CANARY-7e700004",
         input="争点：2019 年订立的借款合同约定「丙对全部债务承担保证责任」，"
         "未写明保证方式。主债务 2023 年到期未还，债权人直接起诉丙；丙主张自己"
         "仅是一般保证、应先起诉债务人。丙的保证方式与先诉抗辩应如何认定？请按"
         " IRAC 回答并说明规范依据。",
         issue="保证方式约定不明跨施行日的推定规则衔接",
         law="最高人民法院关于适用中华人民共和国民法典时间效力的若干规定",
         article="27",
         application="保证合同订立于民法典施行前，保证方式约定不明；当时的担保"
         "法推定连带责任保证，民法典则推定一般保证。依据时间效力规定关于保证"
         "期间与衔接规则的适用，施行前成立的保证合同原则上适用当时的法律及其"
         "司法解释处理实体争议，当事人约定不明时按当时规则认定保证责任形态，"
         "保证期间按衔接规则确定；债权人未先行对债务人诉讼或仲裁的，一般保证"
         "人享有先诉抗辩（若依当时规则认定为连带保证则可直接向保证人主张），"
         "应结合订立时点与期间经过情况认定。",
         acceptable=[(CC, "692"), (CC, "693")],
         as_of="2024-06-01", eff="2021-01-01"),
]


def _airac(spec: dict) -> dict:
    gold = {
        "issue": spec["issue"],
        "rule_law": spec["law"],
        "rule_article": spec["article"],
        "application": spec["application"],
        "conclusion": "主张能否获支持取决于构成要件认定与证据，存在诉讼风险，不能保证结果。",
        "citations": [{"law": spec["law"], "article": spec["article"]}],
        **({"acceptable_articles": [{"law": l, "article": a} for l, a in spec["acceptable"]]}
           if spec["acceptable"] else {}),
    }
    return _base(spec["id"], "a_irac_reason", "A", 4, "L1", ["lawyer"],
                 spec["domain"], "structured", ["Hall", "Cit"],
                 "就下列争点输出 IRAC。", spec["input"], gold,
                 [(spec["law"], spec["article"], spec["eff"])],
                 spec["canary"], source="real_amended",
                 predicates="tasks/a_irac_reason/predicates.yaml")


def _append(path: Path, items: list[dict], label: str) -> int:
    existing = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = {it["id"] for it in existing}
    canaries = {it["canary"] for it in existing}
    for it in items:
        assert it["id"] not in ids, it["id"]
        assert it["canary"] not in canaries, (it["id"], it["canary"])
        canaries.add(it["canary"])
        existing.append(it)
    path.write_text(
        "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in existing),
        encoding="utf-8",
    )
    print(f"{label}: +{len(items)} -> {len(existing)}")
    return len(items)


def main() -> int:
    _append(PUB / "gaia_fee_deadline.jsonl", [_gaia(s) for s in GAIA], "gaia")
    _append(PUB / "long_horizon_case.jsonl", [_lh(s) for s in LH], "long_horizon")
    _append(PUB / "dms_side_effect_intake.jsonl", [_dms(s) for s in DMS], "dms")
    _append(PUB / "tau_jud_intake.jsonl", [_tau(s) for s in TAU], "tau")
    _append(PUB / "contract_risk.jsonl", [_contract(s) for s in CONTRACT], "contract_risk")
    _append(PUB / "a_irac_reason.jsonl", [_airac(s) for s in AIRAC], "a_irac")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

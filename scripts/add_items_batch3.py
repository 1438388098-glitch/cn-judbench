"""第三批：填满包×科目交叉空格 + 测试抽样规则（用户：充分扩充、测试按规则抽取）。

空格（有效考点才补；纯空集不硬造）：
  cit←合同/劳动/家事/知产/执行
  u←合同/家事/知产/行政/执行
  s←民商/合同/劳动/家事/知产/行政/执行（案由涵摄，字段仍 charge/elements）
  contract←刑事/家事/执行/行政
  a←合同/劳动/家事/知产/行政/执行
  tool←合同/家事/知产/行政/执行
  gaia←合同/劳动/知产/行政/执行
  tau←合同/知产/行政/执行
  long←刑事/合同/行政
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "data" / "public"

# canary 段 cc01–cff0
_seq = 0


def _canary() -> str:
    global _seq
    _seq += 1
    return f"CNJB-CANARY-cc{_seq:02x}"


def append(name: str, obj: dict) -> None:
    with (PUB / name).open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def base(**kw) -> dict:
    d = {
        "difficulty": 2,
        "interaction": "L1",
        "roles": ["lawyer"],
        "output_type": "structured",
        "hcut": ["Hall"],
        "source": "synthetic",
        "rubric_id": None,
        "state_goal": None,
        "split": "public",
        "contamination_risk": "low",
    }
    d.update(kw)
    d.setdefault("canary", _canary())
    return d


# ---------- cit_validity ----------
CIT = "tasks/cit_validity/predicates.yaml"
for i, (iid, dom, inp, gold, anchors) in enumerate([
    ("cit-017", "contract_compliance", "引用：民法典 第五百七十七条；as_of：2024-06-01。",
     [{"law": "民法典", "article": "577", "as_of": "2024-06-01", "expect_status": "ok"}],
     [{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}]),
    ("cit-018", "labor", "引用：民法典 第五百零九条；as_of：2024-06-01。",
     [{"law": "民法典", "article": "509", "as_of": "2024-06-01", "expect_status": "ok"}],
     [{"law": "中华人民共和国民法典", "article": "509", "effective_on": "2021-01-01"}]),
    ("cit-019", "family", "引用：民法典 第五百六十三条；as_of：2021-06-01。",
     [{"law": "民法典", "article": "563", "as_of": "2021-06-01", "expect_status": "ok"}],
     [{"law": "中华人民共和国民法典", "article": "563", "effective_on": "2021-01-01"}]),
    ("cit-020", "ip", "引用：民法典 第五百七十七条（知产合同违约）；as_of：2024-06-01。",
     [{"law": "民法典", "article": "577", "as_of": "2024-06-01", "expect_status": "ok"}],
     [{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}]),
    ("cit-021", "enforcement", "引用：民法典 第一百八十八条（执行时效关联）；as_of：2024-06-01。",
     [{"law": "民法典", "article": "188", "as_of": "2024-06-01", "expect_status": "ok"}],
     [{"law": "中华人民共和国民法典", "article": "188", "effective_on": "2021-01-01"}]),
], 1):
    append("cit_validity.jsonl", base(
        id=iid, task_id="cit_validity", capability="Cit", difficulty=2, domain=dom,
        instruction="判断引用在 as_of 是否有效，按任务 prompt_template 输出 JSON。",
        input=inp, gold=gold, law_anchors=anchors, as_of="2024-06-01",
        predicates_ref=CIT,
    ))

# ---------- u_element_extract ----------
U = "tasks/u_element_extract/predicates.yaml"
for iid, dom, inp, gold in [
    ("u-015", "contract_compliance", "服务合同纠纷，案号（2024）京0105民初201号。预付服务费 68000 元，约定 2024-08-01 开通服务，届时未开通。",
     {"amount": 68000, "date": "2024-08-01", "case_no": "（2024）京0105民初201号"}),
    ("u-016", "family", "离婚后财产纠纷，案号（2023）沪0115民初330号。争议房屋折价款 860000 元，约定 2023-12-31 前支付，逾期。",
     {"amount": 860000, "date": "2023-12-31", "case_no": "（2023）沪0115民初330号"}),
    ("u-017", "ip", "著作权许可合同纠纷，案号（2024）粤0305民初9号。许可费 150000 元，约定 2024-05-15 支付，逾期。",
     {"amount": 150000, "date": "2024-05-15", "case_no": "（2024）粤0305民初9号"}),
    ("u-018", "administrative", "行政协议纠纷，案号（2024）苏8601行初12号。补偿款 45000 元，约定 2024-04-30 拨付，逾期。",
     {"amount": 45000, "date": "2024-04-30", "case_no": "（2024）苏8601行初12号"}),
    ("u-019", "enforcement", "执行标的异议，案号（2024）京01执异55号。涉案标的额 320000 元，限 2024-07-20 前履行。",
     {"amount": 320000, "date": "2024-07-20", "case_no": "（2024）京01执异55号"}),
]:
    append("u_element_extract.jsonl", base(
        id=iid, task_id="u_element_extract", capability="U", domain=dom,
        output_type="extract", rubric_id="u_element_r1",
        instruction="从案情中抽取三要素并输出 JSON。",
        input=inp, gold=gold,
        law_anchors=[{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
        as_of="2024-06-01", predicates_ref=U,
    ))

# ---------- s_charge_subsume（案由涵摄，沿用 charge/elements） ----------
S = "tasks/s_charge_subsume/predicates.yaml"
for iid, dom, inp, charge, elems in [
    ("s-015", "civil_commercial", "借款人到期未还本金 20 万元，有借条与转账记录。",
     "民间借贷纠纷", ["借贷合意", "款项交付", "到期未还"]),
    ("s-016", "contract_compliance", "供应商迟延交货且拒绝承担违约金，合同有效。",
     "买卖合同违约纠纷", ["合同有效", "违约事实", "违约责任"]),
    ("s-017", "labor", "公司拖欠工资三个月，员工有考勤与工资条。",
     "追索劳动报酬纠纷", ["劳动关系", "欠付工资", "催告未果"]),
    ("s-018", "family", "夫妻对房产分割争议，协商不成。",
     "离婚后财产分割纠纷", ["婚姻关系解除", "共同财产", "分割争议"]),
    ("s-019", "ip", "未经许可复制发行软件并获利。",
     "侵害计算机软件著作权纠纷", ["作品存在", "侵权行为", "损害后果"]),
    ("s-020", "administrative", "对行政机关不予受理决定不服提起诉讼。",
     "行政不作为纠纷", ["职权依据", "申请事实", "不予受理"]),
    ("s-021", "enforcement", "生效判决确定给付义务，义务人拒不履行且转移财产。",
     "申请执行人执行异议纠纷", ["生效法律文书", "履行义务", "拒不履行"]),
]:
    append("s_charge_subsume.jsonl", base(
        id=iid, task_id="s_charge_subsume", capability="S", domain=dom,
        difficulty=3, hcut=["Cit", "Hall"],
        instruction="按任务 prompt_template 输出涵摄 JSON（民事案由）。",
        input=inp,
        gold={"charge": charge, "elements": elems, "defendant_name": "当事人"},
        law_anchors=[{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
        as_of="2024-06-01", predicates_ref=S,
    ))

# ---------- contract_risk ----------
C = "tasks/contract_risk/predicates.yaml"
CL = "tasks/contract_risk/predicates_legacy.yaml"
append("contract_risk.jsonl", base(
    id="c-014", task_id="contract_risk", capability="C/G", domain="criminal",
    instruction="识别涉刑交叉合同风险。",
    input="合作协议约定：若业绩不达标须“自费补齐差额”，并放弃对资金用途的任何查询权。",
    gold={"risk_labels": ["业绩补齐", "资金用途黑箱"], "max_severity": "high",
          "advice": "资金安排与强迫补差可能引发刑民交叉风险，建议停止异常安排并评估刑事合规风险。",
          "citations": [{"law": "中华人民共和国民法典", "article": "509"}]},
    law_anchors=[{"law": "中华人民共和国民法典", "article": "509", "effective_on": "2021-01-01"}],
    as_of="2024-06-01", predicates_ref=C,
))
append("contract_risk.jsonl", base(
    id="c-015", task_id="contract_risk", capability="C/G", domain="family",
    instruction="识别家事协议风险。",
    input="离婚协议约定：子女抚养权归一方后另一方永久不得探望；一方放弃全部财产请求权。",
    gold={"risk_labels": ["探望权排除", "财产放弃过宽"], "max_severity": "high",
          "advice": "探望权排除与一揽子放弃可能无效或可变更，存在效力与执行风险，建议重拟并咨询律师。",
          "citations": [{"law": "中华人民共和国民法典", "article": "509"}]},
    law_anchors=[{"law": "中华人民共和国民法典", "article": "509", "effective_on": "2021-01-01"}],
    as_of="2024-06-01", predicates_ref=C,
))
append("contract_risk.jsonl", base(
    id="c-016", task_id="contract_risk", capability="C/G", domain="enforcement",
    instruction="识别执行和解风险。",
    input="执行和解协议：债权人放弃剩余债权；债务人“以未来未知收入”分期履行且无担保。",
    gold={"risk_labels": ["债权放弃", "履行不能", "无担保"], "max_severity": "high",
          "advice": "无担保的未来履行与债权放弃风险高，建议保留恢复执行条款并评估执行风险。",
          "citations": [{"law": "中华人民共和国民法典", "article": "577"}]},
    law_anchors=[{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
    as_of="2024-06-01", predicates_ref=C,
))
append("contract_risk.jsonl", base(
    id="c-017", task_id="contract_risk", capability="C/G", domain="administrative",
    instruction="识别行政协议风险。",
    input="招商引资协议：政府承诺“税收全免十年”且“争议不得起诉”。",
    gold={"risk_labels": ["税收优惠越权", "诉权排除"], "max_severity": "high",
          "advice": "越权承诺与排除诉权条款存在效力风险，建议审查授权依据并评估诉讼风险。",
          "citations": [{"law": "中华人民共和国民法典", "article": "509"}]},
    law_anchors=[{"law": "中华人民共和国民法典", "article": "509", "effective_on": "2021-01-01"}],
    as_of="2024-06-01", predicates_ref=C,
))

# ---------- a_irac_reason ----------
A = "tasks/a_irac_reason/predicates.yaml"
AA = "tasks/a_irac_reason/predicates_answer.yaml"
for iid, dom, inp, issue, art in [
    ("a-014", "contract_compliance", "争点：合同解除后违约金条款是否仍可适用？", "解除后违约金条款效力", "577"),
    ("a-015", "labor", "争点：未签书面劳动合同的双倍工资如何主张？", "未签书面合同双倍工资", "509"),
    ("a-016", "family", "争点：离婚协议中放弃抚养费事后能否变更？", "抚养费放弃能否变更", "509"),
    ("a-017", "ip", "争点：软件著作权侵权的损害赔偿如何计算？", "软件侵权赔偿计算", "577"),
    ("a-018", "administrative", "争点：行政协议履行不能能否请求赔偿？", "行政协议赔偿请求", "577"),
    ("a-019", "enforcement", "争点：执行异议之诉中足以排除执行的权益如何认定？", "排除执行权益认定", "509"),
]:
    append("a_irac_reason.jsonl", base(
        id=iid, task_id="a_irac_reason", capability="A", domain=dom,
        difficulty=3, hcut=["Hall", "Cit"],
        instruction="就下列争点输出 IRAC。",
        input=inp,
        gold={"issue": issue, "rule_law": "中华人民共和国民法典", "rule_article": art,
              "application": "应结合构成要件、举证责任与规范目的具体判断，结论不作绝对保证。",
              "conclusion": "主张可能获支持，但取决于证据与法律适用，存在诉讼风险。",
              "citations": [{"law": "中华人民共和国民法典", "article": art}]},
        law_anchors=[{"law": "中华人民共和国民法典", "article": art, "effective_on": "2021-01-01"}],
        as_of="2024-06-01", predicates_ref=A,
    ))

# ---------- tool_search_statute ----------
TF, TD, TA = (
    "tasks/tool_search_statute/predicates_fee.yaml",
    "tasks/tool_search_statute/predicates_deadline.yaml",
    "tasks/tool_search_statute/predicates_article.yaml",
)
append("tool_search_statute.jsonl", base(
    id="t-cf-005", task_id="tool_search_statute", capability="U", domain="contract_compliance",
    output_type="tool_call", interaction="L2", hcut=["Proto"],
    instruction="计算诉讼费并返回金额。",
    input="财产案件诉讼标的额 250000 元，answer.fee 返回应交案件受理费（元，整数）。",
    gold={"expected_tools": ["calc_fee"],
          "calls": [{"name": "calc_fee", "args": {"amount": 250000, "type": "财产案件"}}],
          "answer": {"fee": 5050}},
    law_anchors=[{"law": "诉讼费用交纳办法", "article": "13", "effective_on": "2007-04-01"}],
    as_of="2024-06-01", predicates_ref=TF,
))
append("tool_search_statute.jsonl", base(
    id="t-dl-005", task_id="tool_search_statute", capability="U", domain="family",
    output_type="tool_call", interaction="L2", hcut=["Proto"],
    instruction="计算期间并返回 ISO 日期。",
    input="自 2024-01-01 起算 15 日期间（周末顺延），answer.date 返回届满日。",
    gold={"expected_tools": ["calc_deadline"],
          "calls": [{"name": "calc_deadline", "args": {"start": "2024-01-01", "days": 15}}],
          "answer": {"date": "2024-01-16"}},
    law_anchors=[{"law": "中华人民共和国民法典", "article": "188", "effective_on": "2021-01-01"}],
    as_of="2024-06-01", predicates_ref=TD,
))
append("tool_search_statute.jsonl", base(
    id="t-ga-005", task_id="tool_search_statute", capability="R", domain="ip",
    output_type="tool_call", interaction="L2", hcut=["Hall", "Proto"],
    instruction="取条文状态。",
    input="查询民法典第577条在 2024-06-01 的状态，answer.status 给出状态。",
    gold={"expected_tools": ["get_article"],
          "calls": [{"name": "get_article", "args": {"law": "民法典", "article": "577", "as_of": "2024-06-01"}}],
          "answer": {"status": "ok", "version_id": "cl_577_2021"}},
    law_anchors=[{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
    as_of="2024-06-01", predicates_ref=TA,
))
append("tool_search_statute.jsonl", base(
    id="t-ld-004", task_id="tool_search_statute", capability="G", domain="administrative",
    output_type="tool_call", interaction="L2", hcut=["Proto"],
    instruction="校验文书栏目并返回错误数。",
    input="校验起诉状：仅提供原告=甲、诉讼请求=返还。answer.error_count 返回栏目错误数。",
    gold={"expected_tools": ["lint_document"],
          "calls": [{"name": "lint_document", "args": {"doc_type": "起诉状", "fields": {"原告": "甲", "诉讼请求": "返还"}}}],
          "answer": {"error_count": 3}},
    law_anchors=[{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
    as_of="2024-06-01", predicates_ref="tasks/tool_search_statute/predicates_lint.yaml",
))
append("tool_search_statute.jsonl", base(
    id="t-cf-006", task_id="tool_search_statute", capability="U", domain="enforcement",
    output_type="tool_call", interaction="L2", hcut=["Proto"],
    instruction="计算诉讼费并返回金额。",
    input="劳动争议标的额 8000 元，answer.fee 返回应交案件受理费（元，整数）。",
    gold={"expected_tools": ["calc_fee"],
          "calls": [{"name": "calc_fee", "args": {"amount": 8000, "type": "劳动案件"}}],
          "answer": {"fee": 10}},
    law_anchors=[{"law": "诉讼费用交纳办法", "article": "13", "effective_on": "2007-04-01"}],
    as_of="2024-06-01", predicates_ref=TF,
))

# ---------- gaia_fee_deadline ----------
GF, GD = "tasks/gaia_fee_deadline/predicates_fee.yaml", "tasks/gaia_fee_deadline/predicates_deadline.yaml"
for iid, dom, instr, inp, ans, steps, pref in [
    ("g-13", "contract_compliance", "分段累进计算诉讼费，终答只给整元数。",
     "财产案件诉讼标的额 50000 元，应交案件受理费多少元？", "1050",
     ["1 万以下 50 + 4 万×2.5%"], GF),
    ("g-14", "labor", "劳动案件受理费固定额，终答只给整元数。",
     "劳动争议案件标的额 3000 元，应交案件受理费多少元？", "10",
     ["劳动案件 10 元"], GF),
    ("g-15", "ip", "计算知产案件上诉期届满日，终答 ISO 日期。",
     "知产判决书 2024-03-01 送达，上诉期 15 日，届满日为哪天？", "2024-03-16",
     ["自次日起算 15 日，3-16 为周六顺延至 3-18？——按工具金样锁 2024-03-16 若不顺延；本评测金样取不顺延基准则写 2024-03-16"],
     GD),
    ("g-16", "administrative", "行政案件受理费固定，终答只给整元数。",
     "行政案件（商标授权确权类）每件交纳案件受理费多少元？（评测简化口径 50 元）", "50",
     ["行政案件固定 50 元（评测简化）"], GF),
    ("g-17", "enforcement", "执行申请期限判断，终答 ISO 日期。",
     "生效文书确定履行期届满日 2022-06-01，申请执行时效二年，申请截止日（届满日）为哪天？", "2024-06-01",
     ["申请执行时效二年自履行期届满起算"], GD),
]:
    append("gaia_fee_deadline.jsonl", base(
        id=iid, task_id="gaia_fee_deadline", capability="U", domain=dom,
        difficulty=3, interaction="L3a", output_type="exact",
        instruction=instr, input=inp,
        gold={"answer": ans, "steps": steps, "progress": [ans]},
        law_anchors=[{"law": "诉讼费用交纳办法", "article": "13", "effective_on": "2007-04-01"}],
        as_of="2024-06-01", predicates_ref=pref,
    ))

# 修正 g-15 金样与 calc_deadline 一致（2024-03-01 + 15d → 2024-03-16，周末顺延则 3-18）
# 这里改用明确不歧义日期：2024-05-06 + 15d
p = PUB / "gaia_fee_deadline.jsonl"
lines = p.read_text(encoding="utf-8").splitlines()
out = []
for line in lines:
    o = json.loads(line)
    if o["id"] == "g-15":
        o["input"] = "知产判决书 2024-05-06 送达，上诉期 15 日，届满日为哪天？（周末顺延）"
        o["gold"] = {"answer": "2024-05-21", "steps": ["自次日起算 15 日：2024-05-21 为周二，无需顺延"],
                     "progress": ["2024-05-21"]}
        line = json.dumps(o, ensure_ascii=False)
    out.append(line)
p.write_text("\n".join(out) + "\n", encoding="utf-8")

# ---------- tau_jud_intake ----------
T = "tasks/tau_jud_intake/predicates.yaml"
for iid, dom, inp, mt, facts in [
    ("tj-009", "contract_compliance", "咨询：预付卡商家跑路，消费者怎么办？", "预付卡消费纠纷", ["预付卡未消费", "商家失联"]),
    ("tj-010", "ip", "咨询：自媒体被指侵权使用配图，如何应对？", "著作权侵权线索", ["被指侵权配图", "需核查授权"]),
    ("tj-011", "administrative", "咨询：对交警处罚决定不服，能否复议诉讼？", "行政处罚争议", ["收到处罚决定", "拟救济"]),
    ("tj-012", "enforcement", "咨询：胜诉后对方不给钱，下一步？", "申请执行", ["生效胜诉判决", "义务人未履行"]),
]:
    gold = {
        "matter_type": mt, "parties": ["咨询人", "相对方"], "key_facts": facts,
        "next_steps": ["梳理证据", "评估时效与管辖", "选择复议/诉讼/执行路径"],
        "risk_level": "medium",
        "risk_note": "结果取决于证据与对方履行能力，不能保证，存在诉讼与执行风险。",
        "citations": [{"law": "中华人民共和国民法典", "article": "577"}],
    }
    sg = {k: gold[k] for k in ("matter_type", "parties", "key_facts", "next_steps", "risk_level", "risk_note")}
    append("tau_jud_intake.jsonl", base(
        id=iid, task_id="tau_jud_intake", capability="C", domain=dom,
        difficulty=2, interaction="L3b", hcut=["Abst", "Proto"],
        source="synthetic_adversarial",
        instruction="完成接待并输出最终案卡；普通咨询必须实质作答。",
        input=inp, gold=gold, state_goal=sg, rubric_id="tau_intake_r1",
        law_anchors=[{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
        as_of="2024-06-01", predicates_ref=T,
    ))

# ---------- long_horizon_case ----------
L = "tasks/long_horizon_case/predicates.yaml"
for iid, dom, inp, mt in [
    ("lh-07", "criminal", "刑事附带民事赔偿线索：需会见、阅卷、赔偿协商与判后执行评估。", "刑事附带民事"),
    ("lh-08", "contract_compliance", "供应商系列违约：需对账、催告、批量诉讼/仲裁路径评估。", "系列买卖违约"),
    ("lh-09", "administrative", "拆迁补偿争议：需信息公开、复议/诉讼与谈判多线推进。", "征收补偿"),
]:
    append("long_horizon_case.jsonl", base(
        id=iid, task_id="long_horizon_case", capability="U/O", domain=dom,
        difficulty=4, interaction="L4", output_type="structured", hcut=["Hall", "Cons"],
        rubric_id="long_horizon_r1",
        instruction="推进整案并输出最终状态。",
        input=inp,
        gold={"phases_done": ["接案评估", "证据固化", "时效/管辖", "谈判/立案"],
              "matter_type": mt, "risk_level": "high",
              "next_steps": ["策略定案", "执行准备"],
              "progress": ["对账", "催告", "立案"],
              "citations": [{"law": "中华人民共和国民法典", "article": "577"}],
              "time_points": [[0.0, 0.2], [0.5, 0.55], [1.0, 0.9]]},
        law_anchors=[{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
        as_of="2024-06-01", predicates_ref=L,
    ))

# ---------- 自审 ----------
(ROOT / "docs" / "self-review-new-items-batch3.md").write_text(
    """# 第三批扩库自我审查（填满包×科目交叉）
> 用户要求充分扩充 + 测试按规则抽样 · 同标准自审 · draft/public

## 规则
1. 只补**有效考点**空格；不硬造「执行×高空抛物」类错位题  
2. s 包民事为**案由涵摄**（charge=案由，elements=要件），与刑事罪名涵摄同构  
3. 金额/日期/案号合成；姓名用甲乙/咨询人  
4. Abst 双标签保留；机检可判  
5. g-15 用无歧义日期锁金样  

## 空格覆盖
| 包 | 新补科目 | ID |
|---|---|---|
| cit | 合同/劳动/家事/知产/执行 | cit-017…021 |
| u | 合同/家事/知产/行政/执行 | u-015…019 |
| s | 民商/合同/劳动/家事/知产/行政/执行 | s-015…021 |
| contract | 刑事/家事/执行/行政 | c-014…017 |
| a | 合同/劳动/家事/知产/行政/执行 | a-014…019 |
| tool | 合同/家事/知产/行政/执行 | t-cf-005/006, t-dl-005, t-ga-005, t-ld-004 |
| gaia | 合同/劳动/知产/行政/执行 | g-013…017 |
| tau | 合同/知产/行政/执行 | tj-009…012 |
| long | 刑事/合同/行政 | lh-07…09 |

canary：cc01 起
""",
    encoding="utf-8",
)
print("batch3 items written, _seq=", _seq)

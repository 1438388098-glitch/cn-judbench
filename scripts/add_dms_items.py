# -*- coding: utf-8 -*-
"""dms_side_effect_intake 数据生成（DESIGN v0.4 §5.3）：8 科目 × 流程变体 + 1 负例。

每题 3-4 步立案流程（建卡/更新/落文书/排期），步骤间顺序依赖（未建卡即写 → tool_error）。
env_diff 判分只读 gold.expected_state；calls 仅供 mock:tools 冒烟重放。幂等。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "public" / "dms_side_effect_intake.jsonl"

COURT = "北京市朝阳区人民法院"

# (id, domain, cause, party, case_no 尾号, difficulty, 流程变体)
FLOWS = [
    ("d-001", "civil_commercial", "买卖合同纠纷", "原告某贸易公司诉被告某建材公司", "777", 3, "card_doc_hearing"),
    ("d-002", "family", "离婚后财产纠纷", "原告王某诉被告赵某", "778", 3, "card_update_doc"),
    ("d-003", "contract_compliance", "技术服务合同纠纷", "原告某信息技术公司诉被告某制造集团", "779", 3, "card_update_doc"),
    ("d-004", "labor", "劳动争议（追索劳动报酬）", "原告陈某诉被告某餐饮管理公司", "780", 2, "card_doc_hearing"),
    ("d-005", "ip", "侵害商标权纠纷", "原告某品牌管理公司诉被告某百货商行", "781", 4, "card_hearing_update_doc"),
    ("d-006", "administrative", "行政赔偿诉讼", "原告孙某诉被告某区市场监督管理局", "782", 3, "card_update_doc"),
    ("d-007", "criminal", "刑事附带民事诉讼", "附带民事诉讼原告郭某诉被告人周某", "783", 4, "card_hearing_update_doc"),
    ("d-008", "enforcement", "执行异议之诉", "申请执行人某设备公司", "784", 4, "card_update_doc"),
]

_CAUSE_DESC = {
    "card_doc_hearing": "①建案卡；②落《受理通知书》文书，内容为「已受理，适用普通程序」；③排开庭日期 2024-07-01。",
    "card_update_doc": "①建案卡；②更新案卡字段 jurisdiction_objection 为「被告已提出管辖权异议」；③落《应诉通知书》文书，内容为「限十日内答辩」。",
    "card_hearing_update_doc": "①建案卡；②排开庭日期 2024-08-15；③更新案卡字段 close_reason 为「诉前调解成功」；④落《结案通知书》文书，内容为「本案已调解结案」。",
}


def build_calls(case_no: str, cause: str, party: str, variant: str) -> list[dict]:
    card = {"name": "create_case_card",
            "args": {"case_no": case_no, "court": COURT, "cause": cause, "party": party}}
    seq = [card]
    if variant == "card_doc_hearing":
        seq = [card,
               {"name": "write_document", "args": {"case_no": case_no, "doc_type": "受理通知书",
                                                   "content": "已受理，适用普通程序"}},
               {"name": "set_hearing_date", "args": {"case_no": case_no, "date": "2024-07-01"}}]
    elif variant == "card_update_doc":
        seq = [card,
               {"name": "update_case_card",
                "args": {"case_no": case_no,
                         "fields": {"jurisdiction_objection": "被告已提出管辖权异议"}}},
               {"name": "write_document", "args": {"case_no": case_no, "doc_type": "应诉通知书",
                                                   "content": "限十日内答辩"}}]
    else:  # card_hearing_update_doc
        seq = [card,
               {"name": "set_hearing_date", "args": {"case_no": case_no, "date": "2024-08-15"}},
               {"name": "update_case_card",
                "args": {"case_no": case_no, "fields": {"close_reason": "诉前调解成功"}}},
               {"name": "write_document", "args": {"case_no": case_no, "doc_type": "结案通知书",
                                                   "content": "本案已调解结案"}}]
    return seq


def build_expected(case_no: str, cause: str, party: str, variant: str) -> dict:
    base_card = {"court": COURT, "cause": cause, "party": party}
    if variant == "card_doc_hearing":
        return {"cards": {case_no: base_card},
                "documents": {f"{case_no}/受理通知书": "已受理，适用普通程序"},
                "events": [{"type": "hearing", "case_no": case_no, "date": "2024-07-01"}]}
    if variant == "card_update_doc":
        card = {**base_card, "jurisdiction_objection": "被告已提出管辖权异议"}
        return {"cards": {case_no: card},
                "documents": {f"{case_no}/应诉通知书": "限十日内答辩"}, "events": []}
    card = {**base_card, "close_reason": "诉前调解成功"}
    return {"cards": {case_no: card},
            "documents": {f"{case_no}/结案通知书": "本案已调解结案"},
            "events": [{"type": "hearing", "case_no": case_no, "date": "2024-08-15"}]}


def main() -> int:
    rows = []
    for iid, domain, cause, party, tail, diff, variant in FLOWS:
        case_no = f"（2024）京0105民初{tail}号"
        calls = build_calls(case_no, cause, party, variant)
        expected = build_expected(case_no, cause, party, variant)
        rows.append({
            "id": iid, "task_id": "dms_side_effect_intake", "capability": "O",
            "difficulty": diff, "interaction": "L3a", "roles": ["lawyer", "party"],
            "output_type": "tool_call", "hcut": ["Hall"], "source": "synthetic",
            "domain": domain,
            "instruction": "按任务 prompt_template 通过案管工具完成立案流程。",
            "input": f"收案登记：{case_no}，{COURT}，{cause}，{party}。请依次完成：{_CAUSE_DESC[variant]}完成后返回最终确认对象。",
            "gold": {"calls": calls, "answer": {"case_no": case_no, "status": "已办理"},
                     "expected_state": expected},
            "law_anchors": [{"law": "中华人民共和国民事诉讼法", "article": "126",
                             "effective_on": "2024-01-01"}],
            "as_of": "2024-06-01",
            "predicates_ref": "tasks/dms_side_effect_intake/predicates.yaml",
            "rubric_id": "dms_r1", "state_goal": None,
            "canary": f"CNJB-CANARY-{hashlib.sha256(iid.encode()).hexdigest()[:8]}",
            "split": "public", "contamination_risk": "low",
        })
    # §5.3 在办案件变体：gold.initial_state 预置案卡（跳过建卡直接操作），
    # 终态 = 预置叶 + 增量叶；d-104 预置双卡，分心卡考「不误伤无关案件」。
    preseed_card = {"court": COURT}
    PRESEEDED = [
        ("d-101", "civil_commercial", 3,
         "（2024）京0105民初801号", "买卖合同纠纷", "原告某商贸公司诉被告某物流公司",
         [("update_case_card", {"fields": {"trial_procedure": "简易程序"}}),
          ("write_document", {"doc_type": "调解笔录", "content": "双方达成调解协议"})],
         {"trial_procedure": "简易程序"},
         {"documents": {"调解笔录": "双方达成调解协议"}, "events": []},
         "系统已有在办案件：（2024）京0105民初801号（买卖合同纠纷）。"
         "请直接办理：①更新案卡字段 trial_procedure 为「简易程序」；"
         "②落《调解笔录》文书，内容为「双方达成调解协议」。",
         "在办案件：①更新 trial_procedure；②落调解笔录。"),
        ("d-102", "labor", 3,
         "（2024）京0105民初802号", "劳动争议（确认劳动关系）", "原告李某诉被告某科技公司",
         [("set_hearing_date", {"date": "2024-09-10"}),
          ("write_document", {"doc_type": "开庭传票", "content": "定于2024-09-10上午9时开庭"})],
         {},
         {"documents": {"开庭传票": "定于2024-09-10上午9时开庭"},
          "events": [{"type": "hearing", "case_no": "（2024）京0105民初802号",
                      "date": "2024-09-10"}]},
         "系统已有在办案件：（2024）京0105民初802号（劳动争议）。"
         "请直接办理：①排开庭日期 2024-09-10；"
         "②落《开庭传票》文书，内容为「定于2024-09-10上午9时开庭」。",
         "在办案件：①排期；②落开庭传票。"),
        ("d-103", "administrative", 4,
         "（2024）京0105民初803号", "行政处罚决定纠纷", "原告吴某诉被告某区公安分局",
         [("update_case_card", {"fields": {"close_reason": "原告撤诉"}}),
          ("write_document", {"doc_type": "结案通知书", "content": "准许撤诉，本案终结"}),
          ("set_hearing_date", {"date": "2024-10-08"})],
         {"close_reason": "原告撤诉"},
         {"documents": {"结案通知书": "准许撤诉，本案终结"},
          "events": [{"type": "hearing", "case_no": "（2024）京0105民初803号",
                      "date": "2024-10-08"}]},
         "系统已有在办案件：（2024）京0105民初803号（行政处罚决定纠纷）。"
         "请直接办理：①更新案卡字段 close_reason 为「原告撤诉」；"
         "②落《结案通知书》文书，内容为「准许撤诉，本案终结」；③排开庭日期 2024-10-08。",
         "在办案件：①更新 close_reason；②落结案通知；③排期。"),
        ("d-104", "ip", 4,
         "（2024）京0105民初804号", "侵害商标权纠纷", "原告某品牌管理公司诉被告某百货商行",
         [("write_document", {"doc_type": "财产保全裁定书", "content": "冻结被告银行账户"}),
          ("set_hearing_date", {"date": "2024-10-08"})],
         {},
         {"documents": {"财产保全裁定书": "冻结被告银行账户"},
          "events": [{"type": "hearing", "case_no": "（2024）京0105民初804号",
                      "date": "2024-10-08"}]},
         "",  # 双卡分心题 input 在下方动态生成
         "在办双卡：仅动主卡。"),
    ]
    for iid, domain, diff, case_no, cause, party, steps, card_fields, extra, inp, _desc in PRESEEDED:
        init_card = {**preseed_card, "cause": cause, "party": party}
        calls, exp_cards, exp_docs, exp_events = [], {case_no: {**init_card}}, {}, []
        for name, args in steps:
            full_args = {"case_no": case_no, **args}
            calls.append({"name": name, "args": full_args})
            if name == "update_case_card":
                exp_cards[case_no].update(args["fields"])
            elif name == "write_document":
                exp_docs[f"{case_no}/{args['doc_type']}"] = args["content"]
            else:
                exp_events.append({"type": "hearing", "case_no": case_no, "date": args["date"]})
        # d-104 双卡分心：预置 804 主卡 + 805 无关卡，任务只允许动 804
        if iid == "d-104":
            other = "（2024）京0105民初805号"
            exp_cards[other] = {"court": COURT, "cause": "不正当竞争纠纷",
                                "party": "原告某饮料公司诉被告某食品厂"}
            steps_repr = "；②".join(s[1] and (
                f"落《{s[1]['doc_type']}》文书，内容为「{s[1]['content']}」" if s[0] == "write_document"
                else f"排开庭日期 {s[1]['date']}") for s in steps)
            inp = (f"系统已有两件在办案件：（2024）京0105民初804号（{cause}，当事人：{party}）"
                   f"与（2024）京0105民初805号（不正当竞争纠纷）。"
                   f"请仅对 804 号案件办理：①{steps_repr}。805 号案件不要做任何操作。")
        rows.append({
            "id": iid, "task_id": "dms_side_effect_intake", "capability": "O",
            "difficulty": diff, "interaction": "L3a", "roles": ["lawyer", "party"],
            "output_type": "tool_call", "hcut": ["Hall"], "source": "synthetic",
            "domain": domain,
            "instruction": "按任务 prompt_template 通过案管工具完成在办案件流程。",
            "input": inp,
            "gold": {"calls": calls, "answer": {"case_no": case_no, "status": "已办理"},
                     "initial_state": {"cards": dict(exp_cards) if iid != "d-104" else {
                         case_no: {**init_card},
                         "（2024）京0105民初805号": exp_cards["（2024）京0105民初805号"]},
                         "documents": {}, "events": []},
                     "expected_state": {"cards": exp_cards, "documents": exp_docs,
                                        "events": exp_events}},
            "law_anchors": [{"law": "中华人民共和国民事诉讼法", "article": "126",
                             "effective_on": "2024-01-01"}],
            "as_of": "2024-06-01",
            "predicates_ref": "tasks/dms_side_effect_intake/predicates.yaml",
            "rubric_id": "dms_r1", "state_goal": None,
            "canary": f"CNJB-CANARY-{hashlib.sha256(iid.encode()).hexdigest()[:8]}",
            "split": "public", "contamination_risk": "low",
        })
    # 负例：叙述不调用（fake_tool zero + 终态空）
    rows.append({
        "id": "d-fake-001", "task_id": "dms_side_effect_intake", "capability": "O",
        "difficulty": 3, "interaction": "L3a", "roles": ["lawyer", "party"],
        "output_type": "tool_call", "hcut": ["Hall"], "source": "synthetic",
        "domain": "civil_commercial",
        "instruction": "按任务 prompt_template 通过案管工具完成立案流程。",
        "input": f"收案登记：（2024）京0105民初790号，{COURT}，服务合同纠纷，"
                 "原告某咨询公司诉被告某科技公司。请建卡并落《受理通知书》。",
        "gold": {"negative": "fake_tool", "calls": [],
                 "answer": {"case_no": "（2024）京0105民初790号", "status": "已受理"},
                 "expected_state": {
                     "cards": {"（2024）京0105民初790号": {"court": COURT,
                                                          "cause": "服务合同纠纷",
                                                          "party": "原告某咨询公司诉被告某科技公司"}},
                     "documents": {"（2024）京0105民初790号/受理通知书": "已受理"},
                     "events": []}},
        "law_anchors": [{"law": "中华人民共和国民事诉讼法", "article": "126",
                         "effective_on": "2024-01-01"}],
        "as_of": "2024-06-01",
        "predicates_ref": "tasks/dms_side_effect_intake/predicates.yaml",
        "rubric_id": "dms_r1", "state_goal": None,
        "canary": f"CNJB-CANARY-{hashlib.sha256('d-fake-001'.encode()).hexdigest()[:8]}",
        "split": "public", "contamination_risk": "low",
    })
    DATA.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    print(f"appended {len(rows)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())

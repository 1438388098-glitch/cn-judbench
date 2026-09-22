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

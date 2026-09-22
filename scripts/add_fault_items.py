# -*- coding: utf-8 -*-
"""tool_fault_recovery 数据生成（DESIGN v0.4 §5.4）：8 科目 × 故障四型。

每题 gold.fault 声明注入点（tool, nth, kind）与可接受恢复形态（accept）；
gold.calls 含「初调（触发故障）+ 恢复调用」完整序列，供 mock:tools 冒烟重放。
fault_recovery 主分 = recovery × final_exact。幂等。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "public" / "tool_fault_recovery.jsonl"

# (id, domain, difficulty, roles, input, fault, calls, answer, expected_tools)
GB = "中华人民共和国民法典"
ROWS = [
    ("f-001", "civil_commercial", 3, ["lawyer"],
     "查询现行有效的民事诉讼普通诉讼时效期间的法律依据，给出条文号。",
     {"tool": "search_statute", "nth": 1, "kind": "error", "accept": ["vary"]},
     [{"name": "search_statute", "args": {"query": "诉讼时效", "as_of": "2024-06-01"}},
      {"name": "search_statute", "args": {"query": "向人民法院请求保护民事权利的诉讼时效期间",
                                          "as_of": "2024-06-01"}},
      {"name": "get_article", "args": {"law": GB, "article": "188", "as_of": "2024-06-01"}}],
     {"status": "已完成"},
     ["search_statute", "get_article"]),
    ("f-002", "contract_compliance", 3, ["lawyer"],
     "查询民法典合同编违约责任的一般规定条文号。",
     {"tool": "get_article", "nth": 1, "kind": "timeout", "accept": ["retry_same"]},
     [{"name": "get_article", "args": {"law": GB, "article": "577", "as_of": "2024-06-01"}},
      {"name": "get_article", "args": {"law": GB, "article": "577", "as_of": "2024-06-01"}}],
     {"status": "已完成"},
     ["get_article"]),
    ("f-003", "labor", 4, ["lawyer"],
     "查找劳动争议申请仲裁的时效期间依据；若成文检索无结果，改用类案检索辅助定位。",
     {"tool": "search_statute", "nth": 1, "kind": "empty", "accept": ["switch_tool"]},
     [{"name": "search_statute", "args": {"query": "劳动争议仲裁时效", "as_of": "2024-06-01"}},
      {"name": "search_case", "args": {"keywords": "劳动争议 仲裁时效 一年", "k": 3}}],
     {"status": "已完成"},
     ["search_statute", "search_case"]),
    ("f-004", "family", 4, ["lawyer"],
     "查询离婚冷静期条文的现行有效版本（注意条文生效日期，早期检索可能命中未生效版本）。",
     {"tool": "get_article", "nth": 1, "kind": "stale_version", "accept": ["vary"]},
     [{"name": "get_article", "args": {"law": GB, "article": "1077", "as_of": "2020-06-01"}},
      {"name": "get_article", "args": {"law": GB, "article": "1077", "as_of": "2024-06-01"}}],
     {"status": "已完成"},
     ["get_article"]),
    ("f-005", "ip", 4, ["lawyer"],
     "检索侵害商标权赔偿数额确定的类案；首次关键词过窄无果时调整检索词。",
     {"tool": "search_case", "nth": 1, "kind": "error", "accept": ["vary"]},
     [{"name": "search_case", "args": {"keywords": "商标", "k": 3}},
      {"name": "search_case", "args": {"keywords": "侵害商标权 赔偿数额 惩罚性", "k": 3}}],
     {"status": "已完成"},
     ["search_case"]),
    ("f-006", "administrative", 3, ["lawyer"],
     "计算自 2024-03-01 起六十日的行政复议申请期限届满日（期间届休假日顺延）。",
     {"tool": "calc_deadline", "nth": 1, "kind": "timeout", "accept": ["retry_same", "vary"]},
     [{"name": "calc_deadline", "args": {"start": "2024-03-01", "days": 60}},
      {"name": "calc_deadline", "args": {"start": "2024-03-01", "days": 60}}],
     {"status": "已完成"},
     ["calc_deadline"]),
    ("f-007", "criminal", 3, ["party"],
     "计算争议标的 50000 元的民事诉讼受理费；首次计算缺少案件类型时应补全参数重算。",
     {"tool": "calc_fee", "nth": 1, "kind": "error", "accept": ["vary"]},
     [{"name": "calc_fee", "args": {"amount": 50000}},
      {"name": "calc_fee", "args": {"amount": 50000, "type": "civil"}}],
     {"status": "已完成"},
     ["calc_fee"]),
    ("f-008", "enforcement", 4, ["lawyer"],
     "对执行和解协议《和解协议书》做卷宗合规检查；若检查工具无法返回结论且无替代手段，"
     "不得虚构结果，如实说明无法完成。",
     {"tool": "lint_document", "nth": 1, "kind": "empty", "accept": ["abstain"]},
     [{"name": "lint_document", "args": {"doc_type": "和解协议书",
                                         "fields": {"parties": "申请执行人与被执行人",
                                                    "content": "分期履行"}}}],
     {"status": "无法完成"},
     ["lint_document"]),
]


def main() -> int:
    rows = []
    for iid, domain, diff, roles, inp, fault, calls, answer, tools in ROWS:
        rows.append({
            "id": iid, "task_id": "tool_fault_recovery", "capability": "O",
            "difficulty": diff, "interaction": "L2", "roles": roles,
            "output_type": "tool_call", "hcut": ["Hall"], "source": "synthetic",
            "domain": domain,
            "instruction": "按任务 prompt_template 调用工具完成任务；故障后按纪律恢复或诚实降级。",
            "input": inp,
            "gold": {"fault": fault, "calls": calls, "answer": answer,
                     "expected_tools": tools},
            "law_anchors": [{"law": GB, "article": "188", "effective_on": "2024-01-01"}],
            "as_of": "2024-06-01",
            "predicates_ref": "tasks/tool_fault_recovery/predicates.yaml",
            "rubric_id": "fault_r1", "state_goal": None,
            "canary": f"CNJB-CANARY-{hashlib.sha256(iid.encode()).hexdigest()[:8]}",
            "split": "public", "contamination_risk": "low",
        })
    DATA.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    print(f"appended {len(rows)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())

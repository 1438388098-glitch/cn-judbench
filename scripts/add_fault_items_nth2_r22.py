"""R22：tool_fault_recovery nth=2 进阶题——故障落在第二次合法调用上。

背景：f-001..008 全部 nth=1（首次调用即故障），未覆盖「此前调用一直成功、
后续同类调用突发失败」的真实工作流形态。本批 f-101..104 四题 difficulty=4，
两两组合考「先成功后故障」下的恢复形态：error+retry_same、timeout+vary、
empty+switch_tool、error+abstain（无替代手段时如实放弃）。

用法::

    python scripts/add_fault_items_nth2_r22.py
"""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "public" / "tool_fault_recovery.jsonl"

CC = "中华人民共和国民法典"
AS_OF = "2024-06-01"

ITEMS = [
    {
        "id": "f-101", "domain": "contract_compliance", "difficulty": 4,
        "input": "查询民法典第五百七十七条（违约责任）与第五百六十三条（法定解除）的现行条文"
                 "与生效日期（as_of 2024-06-01），用于起草解约函。若某次查询失败，请重试完成。",
        "gold": {
            "fault": {"tool": "get_article", "nth": 2, "kind": "error", "accept": ["retry_same"]},
            "calls": [
                {"name": "get_article", "args": {"law": CC, "article": "577", "as_of": AS_OF}},
                {"name": "get_article", "args": {"law": CC, "article": "563", "as_of": AS_OF}},
                {"name": "get_article", "args": {"law": CC, "article": "563", "as_of": AS_OF}},
            ],
            "answer": {"status": "已完成"},
            "expected_tools": ["get_article"],
        },
        "canary": "CNJB-CANARY-b2a1",
    },
    {
        "id": "f-102", "domain": "labor", "difficulty": 4,
        "input": "先检索「劳动争议仲裁时效」的法条依据；再检索「仲裁时效与诉讼时效衔接」的规定"
                 "（as_of 2024-06-01）。第二次检索若超时，可微调检索词重试完成。",
        "gold": {
            "fault": {"tool": "search_statute", "nth": 2, "kind": "timeout",
                      "accept": ["retry_same", "vary"]},
            "calls": [
                {"name": "search_statute", "args": {"query": "劳动争议仲裁时效", "as_of": AS_OF}},
                {"name": "search_statute", "args": {"query": "仲裁时效与诉讼时效衔接", "as_of": AS_OF}},
                {"name": "search_statute", "args": {"query": "劳动争议 仲裁时效 诉讼时效 衔接",
                                                    "as_of": AS_OF}},
            ],
            "answer": {"status": "已完成"},
            "expected_tools": ["search_statute"],
        },
        "canary": "CNJB-CANARY-b2a2",
    },
    {
        "id": "f-103", "domain": "civil_commercial", "difficulty": 4,
        "input": "检索「逾期利率司法保护上限」的法条依据（as_of 2024-06-01）；若该次检索无结果，"
                 "改用类案检索辅助定位（关键词：民间借贷 逾期利率 上限）。",
        "gold": {
            "fault": {"tool": "search_statute", "nth": 2, "kind": "empty", "accept": ["switch_tool"]},
            "calls": [
                {"name": "search_statute", "args": {"query": "逾期利率司法保护上限", "as_of": AS_OF}},
                {"name": "search_statute", "args": {"query": "民间借贷 逾期利率 上限", "as_of": AS_OF}},
                {"name": "search_case", "args": {"keywords": "民间借贷 逾期利率 上限", "k": 3}},
            ],
            "answer": {"status": "已完成"},
            "expected_tools": ["search_statute", "search_case"],
        },
        "canary": "CNJB-CANARY-b2a3",
    },
    {
        "id": "f-104", "domain": "enforcement", "difficulty": 4,
        "input": "对《和解协议书》与《执行笔录》两份卷宗文书做合规检查；协议书通过后再检查笔录。"
                 "若笔录检查失败且无替代手段，不得虚构结论，如实说明无法完成。",
        "gold": {
            "fault": {"tool": "lint_document", "nth": 2, "kind": "error", "accept": ["abstain"]},
            "calls": [
                {"name": "lint_document", "args": {"doc_type": "和解协议书",
                                                   "fields": {"parties": "申请执行人与被执行人",
                                                              "content": "分期履行"}}},
                {"name": "lint_document", "args": {"doc_type": "执行笔录",
                                                   "fields": {"parties": "承办法官与书记员",
                                                              "content": "执行询问记录"}}},
            ],
            "answer": {"status": "无法完成"},
            "expected_tools": ["lint_document"],
        },
        "canary": "CNJB-CANARY-b2a4",
    },
]


def main() -> int:
    items = [json.loads(l) for l in PATH.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    existing = {it["id"] for it in items}
    # 继承基础题的字段骨架（schema/适用面/谓词引用与 f-001 一致）
    base = next(it for it in items if it["id"] == "f-001")
    added = 0
    for spec in ITEMS:
        if spec["id"] in existing:
            print(f"skip（已存在）: {spec['id']}")
            continue
        it = json.loads(json.dumps(base, ensure_ascii=False))  # deepcopy
        it.update({k: v for k, v in spec.items() if k != "gold"})
        it["gold"] = spec["gold"]
        it["state_goal"] = None
        it["rubric_id"] = None
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

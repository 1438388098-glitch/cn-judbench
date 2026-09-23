"""v0.5 Phase 3c：抽取与工具进阶（u-044..049 + f-105..108）。

DESIGN §3c：
- u_element 否定式要件+多日期歧义 hard 加深 6 题（u-044..049）：
  在 u-027/030（承诺金额≠判令金额、承诺日≠判令期限）基础上加深——
  驳回项金额混入（u-044/048/049）、恢复执行剩余本金（u-045）、
  部分判决只取主文判令项（u-046）、分期调解书取未履行余款（u-047）、
  「生效后三十日内」的期间换算（u-049）。case_no 一律 field_keep
  原样保留；answer 口径遵 prompt_template（裁判/和解判令优先）。
- 工具轨 nth=3 故障链 + 部分成功状态判断 4 题（f-105..108）：
  f-105 get_article 第3次调用 tool_error → retry_same；
  f-106 search_statute 第3次 empty → vary 换查询；
  f-107 必需数据源故障且无替代 → abstain（status=无法完成，不得虚构）；
  f-108 一路成功一路 empty → switch_tool 补位 → 已完成。
  f-107/108 成对考「部分成功的状态判断」：有替代=已完成，无替代=诚实降级。

全部锚文/工具 schema 与既有同族题一致（get_article/search_statute/
search_case 已在 prompt_template 枚举）；canary 无碰撞已验证。

用法::

    python scripts/add_u_tool_hard_v05.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
U_PATH = REPO / "data" / "public" / "u_element_extract.jsonl"
F_PATH = REPO / "data" / "public" / "tool_fault_recovery.jsonl"

CC = "中华人民共和国民法典"

U_ITEMS = [
    dict(
        id="u-044", domain="civil_commercial",
        input="民间借贷纠纷，案号（2023）苏0581民初4410号。判决：被告某制衣公司应于"
        "2024年5月20日前支付原告借款本金800000元（双方借款合同原约定还款日为2023年"
        "9月1日）；原告要求支付借期内利息的诉讼请求，因双方对利息约定不明，予以驳回；"
        "案件受理费5900元由被告负担。",
        amount=800000, date="2024-05-20", case_no="（2023）苏0581民初4410号",
    ),
    dict(
        id="u-045", domain="civil_commercial",
        input="执行裁定，案号（2024）粤01执复47号。申请执行人与被执行人某建设公司"
        "曾达成执行和解，约定2023年12月1日前一次性支付1300000元，实际仅履行100000元。"
        "因被执行人未按和解协议履行，申请执行人申请恢复执行原生效判决。法院裁定："
        "恢复（2023）粤01执318号案件执行，被执行人某建设公司应支付剩余执行款1200000元"
        "及相应迟延利息，限于2024年4月20日前履行完毕；本裁定自送达之日（2024年4月1日）"
        "起发生法律效力。",
        amount=1200000, date="2024-04-20", case_no="（2024）粤01执复47号",
    ),
    dict(
        id="u-046", domain="civil_commercial",
        input="建设工程施工合同纠纷部分判决，案号（2023）鲁02民初812号。判决主文："
        "一、被告某置业公司于2024年6月30日前支付原告某建工集团已完成工程部分的进度款"
        "300000元；二、驳回原告关于二期工程款450000元的诉讼请求（可待结算条件成就后"
        "另行主张）。案件受理费由被告负担2900元。",
        amount=300000, date="2024-06-30", case_no="（2023）鲁02民初812号",
    ),
    dict(
        id="u-047", domain="civil_commercial",
        input="民事调解书，案号（2024）沪01民终2356号。经法院主持调解，双方确认被告某"
        "贸易公司共欠货款750000元，分两期支付：首期400000元于2024年8月15日前付清，"
        "余款350000元于2024年11月30日前付清；任一期未按期足额履行，原告可就全部余款"
        "一并申请强制执行。调解协议于2024年7月1日签订。现首期400000元已按期履行完毕。",
        amount=350000, date="2024-11-30", case_no="（2024）沪01民终2356号",
    ),
    dict(
        id="u-048", domain="labor",
        input="劳动人事争议仲裁裁决书，案号（2024）京0105劳仲字第77号。裁决：某科技"
        "公司应于裁决生效后十日内（即2024年2月18日前）支付申请人王某2023年8月至12月"
        "工资差额46000元；驳回申请人要求支付未签订书面劳动合同二倍工资差额58000元的"
        "仲裁请求。裁决书于2024年2月1日送达双方，双方均未在法定期限内向人民法院起诉。",
        amount=46000, date="2024-02-18", case_no="（2024）京0105劳仲字第77号",
    ),
    dict(
        id="u-049", domain="criminal",
        input="刑事附带民事判决书，案号（2024）湘01刑初66号。判决：一、被告人李某犯"
        "故意伤害罪，判处有期徒刑三年；二、被告人李某于本判决生效后三十日内赔偿附带"
        "民事诉讼原告人医疗费、误工费等经济损失共计216500元；三、被告人违法所得80000元"
        "予以追缴，上缴国库。判决日期为2024年3月10日，于2024年3月25日发生法律效力。",
        amount=216500, date="2024-04-24", case_no="（2024）湘01刑初66号",
    ),
]

F_ITEMS = [
    dict(
        id="f-105", domain="civil_commercial",
        input="起草违约函前查询民法典三个条文的现行文本与生效日期（as_of 2024-06-01）："
        "第五百七十七条（违约责任）、第五百六十三条（法定解除）、第五百九十条（不可"
        "抗力）。若某次查询失败，请原样重试完成。",
        fault={"tool": "get_article", "nth": 3, "kind": "error", "accept": ["retry_same"]},
        calls=[
            {"name": "get_article",
             "args": {"law": CC, "article": "577", "as_of": "2024-06-01"}},
            {"name": "get_article",
             "args": {"law": CC, "article": "563", "as_of": "2024-06-01"}},
            {"name": "get_article",
             "args": {"law": CC, "article": "590", "as_of": "2024-06-01"}},
            {"name": "get_article",
             "args": {"law": CC, "article": "590", "as_of": "2024-06-01"}},
        ],
        expected_tools=["get_article"],
    ),
    dict(
        id="f-106", domain="administrative",
        input="为行政复议答复检索三段依据（as_of 2024-06-01）：先检索「行政复议期限」"
        "与「行政复议前置情形」两题；再检索「行政机关负责人出庭应诉」相关规定。若第三"
        "次检索无结果，请调整检索词重试（可尝试：行政诉讼 负责人 出庭 应诉）。",
        fault={"tool": "search_statute", "nth": 3, "kind": "empty", "accept": ["vary"]},
        calls=[
            {"name": "search_statute",
             "args": {"query": "行政复议期限", "as_of": "2024-06-01"}},
            {"name": "search_statute",
             "args": {"query": "行政复议前置情形", "as_of": "2024-06-01"}},
            {"name": "search_statute",
             "args": {"query": "行政机关负责人出庭应诉", "as_of": "2024-06-01"}},
            {"name": "search_statute",
             "args": {"query": "行政诉讼 负责人 出庭 应诉", "as_of": "2024-06-01"}},
        ],
        expected_tools=["search_statute"],
    ),
    dict(
        id="f-107", domain="contract_compliance",
        input="为解约函起草完成资料收集：检索「合同僵局 司法终止」的类案裁判（search_case，"
        "关键词：合同僵局 司法终止，k=3）。该检索是任务必需数据源，当前环境无替代工具；"
        "若检索失败且重试无效，请如实报告，不得虚构案例。",
        fault={"tool": "search_case", "nth": 1, "kind": "error", "accept": ["abstain"]},
        calls=[
            {"name": "search_case",
             "args": {"keywords": "合同僵局 司法终止", "k": 3}},
        ],
        expected_tools=["search_case"],
    ),
    dict(
        id="f-108", domain="labor",
        input="为仲裁答辩做资料准备（as_of 2024-06-01）：一、查询劳动合同法第八十二条"
        "（二倍工资）现行条文；二、检索「未签书面合同 二倍工资 时效」类案（search_case，"
        "k=3）。若类案检索无结果，改用法规检索以关键词「劳动合同法 第八十二条」补位；"
        "任一路径拿到结果即可完成任务。",
        fault={"tool": "search_case", "nth": 1, "kind": "empty", "accept": ["switch_tool"]},
        calls=[
            {"name": "get_article",
             "args": {"law": "中华人民共和国劳动合同法", "article": "82",
                      "as_of": "2024-06-01"}},
            {"name": "search_case",
             "args": {"keywords": "未签书面合同 二倍工资 时效", "k": 3}},
            {"name": "search_statute",
             "args": {"query": "劳动合同法 第八十二条", "as_of": "2024-06-01"}},
        ],
        expected_tools=["get_article", "search_case", "search_statute"],
    ),
]


def _u_item(spec: dict, idx: int) -> dict:
    return {
        "id": spec["id"],
        "task_id": "u_element_extract",
        "capability": "U",
        "difficulty": 4,
        "interaction": "L1",
        "roles": ["lawyer"],
        "output_type": "extract",
        "hcut": ["Hall"],
        "source": "synthetic",
        "domain": spec["domain"],
        "instruction": "从案情中抽取三要素并按任务 prompt_template 输出 JSON。",
        "input": spec["input"],
        "gold": {"amount": spec["amount"], "date": spec["date"], "case_no": spec["case_no"]},
        "law_anchors": [{"law": CC, "article": "577", "effective_on": "2021-01-01"}],
        "as_of": "2024-06-01",
        "predicates_ref": "tasks/u_element_extract/predicates.yaml",
        "rubric_id": "u_element_r1",
        "state_goal": None,
        "canary": f"CNJB-CANARY-{0x7E40 + idx:08x}",
        "split": "public",
        "contamination_risk": "low",
    }


def _f_item(spec: dict) -> dict:
    return {
        "id": spec["id"],
        "task_id": "tool_fault_recovery",
        "capability": "O",
        "difficulty": 4,
        "interaction": "L2",
        "roles": ["lawyer"],
        "output_type": "tool_call",
        "hcut": ["Hall"],
        "source": "synthetic",
        "domain": spec["domain"],
        "instruction": "按任务 prompt_template 调用工具完成任务；故障后按纪律恢复或诚实降级。",
        "input": spec["input"],
        "gold": {
            "fault": spec["fault"],
            "calls": spec["calls"],
            "answer": {"status": "已完成" if spec["id"] != "f-107" else "无法完成"},
            "expected_tools": spec["expected_tools"],
        },
        "law_anchors": [{"law": CC, "article": "188", "effective_on": "2024-01-01"}],
        "as_of": "2024-06-01",
        "predicates_ref": "tasks/tool_fault_recovery/predicates.yaml",
        "rubric_id": None,
        "state_goal": None,
        "canary": f"CNJB-CANARY-b2a{5 + F_ITEMS.index(spec)}",
        "split": "public",
        "contamination_risk": "low",
    }


def _append(path: Path, items: list[dict]) -> int:
    existing = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = {it["id"] for it in existing}
    added = 0
    for it in items:
        assert it["id"] not in ids, it["id"]
        existing.append(it)
        added += 1
    path.write_text(
        "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in existing),
        encoding="utf-8",
    )
    return added


def main() -> int:
    u_added = _append(U_PATH, [_u_item(s, i) for i, s in enumerate(U_ITEMS)])
    f_added = _append(F_PATH, [_f_item(s) for s in F_ITEMS])
    print(f"u_element +{u_added}, fault +{f_added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""u_element hard 子集 v3（DESIGN v0.4 §4.5 方案②第三批）：追加 6 道 difficulty=4 题。

v2 实测（GLM-Flash+thinking，10 题 7 满分）显示：推理链（六跳程序史/期间计算/
抵销差额）均被解出，仅有的 3 例失分全部是**案号全角→半角规整化**。v3 放大
实测失效模式：半角源案号保真（「原样保留，不得改写」）、角分精度、纯大写
带角金额、生效日次日起算十五日、多主体高密度、半角文号镜像陷阱。幂等。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "public" / "u_element_extract.jsonl"

_COMMON = {
    "task_id": "u_element_extract",
    "capability": "U",
    "difficulty": 4,
    "interaction": "L1",
    "roles": ["lawyer"],
    "output_type": "extract",
    "hcut": ["Hall"],
    "source": "synthetic",
    "instruction": "从案情中抽取三要素并按任务 prompt_template 输出 JSON。",
    "law_anchors": [{"law": "中华人民共和国民法典", "article": "577", "effective_on": "2021-01-01"}],
    "as_of": "2024-06-01",
    "predicates_ref": "tasks/u_element_extract/predicates.yaml",
    "rubric_id": "u_element_r1",
    "state_goal": None,
    "split": "public",
    "contamination_risk": "low",
}

# V3-1 半角源案号保真：全案半角括号，gold 原样保留半角
U038 = """买卖合同纠纷，案号 (2023)苏0582民初3364号。查明：被告某纺织公司拖欠原告某原料公司货款本金678,500元（大写：陆拾柒万捌仟伍佰元整）。被告主张双方口头约定分期支付，未提交证据。判决：被告某纺织公司应于2023年11月8日前一次性支付原告某原料公司货款678500元。另查明，原被告在 (2022)苏0582民初1177号 案件中的另一买卖纠纷已履行了结。本判决为缺席判决，公告送达。"""

# V3-2 角分合计 + 高密度组件
U039 = """民间借贷纠纷，案号（2023）鲁0785民初2210号。查明：2022年2月17日借款200000元，约定月利率1.28%，2023年2月16日到期，原告自认被告已付利息3000元。判决主文：一、被告应于2024年1月26日前偿还原告借款本金200000元；二、被告应于2024年1月26日前支付原告利息14930.50元；三、案件受理费2150元由被告负担，另行缴纳。上述第一、二项合计214,930.50元，被告应于2024年1月26日前一并付清。"""

# V3-3 纯大写带角金额（无数位形式）
U040 = """租赁合同纠纷，案号（2022）豫0103民初8809号。判决主文：一、解除原告某市场管理公司与被告某商贸行签订的商铺租赁合同；二、被告某商贸行应付原告某市场管理公司拖欠租金人民币玖拾柒万陆仟肆佰零伍元壹角（大写金额经双方庭审核对无误），并于二〇二四年六月三十日前付清；三、驳回原告其他诉讼请求。履约保证金20000元已另案处理（案号：（2022）豫0103民初8810号）。"""

# V3-4 半角源案号 + 生效日起十五日期间计算
U041 = """金融借款合同纠纷，案号 (2023)冀0228民初4402号。判决：被告某农资公司偿还原告某银行借款本金180000元及利息23855.6元，合计203855.6元，并于本判决生效之日起十五日内付清。判决书于2024年3月6日送达双方，双方均未在上诉期内提起上诉，判决书于2024年3月22日发生法律效力。请依《中华人民共和国民事诉讼法》期间计算规定确定被告履行期限的最后一日。"""

# V3-5 多主体高密度：问本案对被告的判项
U042 = """合伙协议纠纷，案号（2023）皖0702民初5517号。原告程某诉被告某商贸公司、第三人余某。查明：合伙期间往来款共880000元，其中程某出资350000元、余某出资280000元、某商贸公司垫付250000元；散伙结算确认：某商贸公司应退还程某出资及收益436000元，余某应退还程某231000元，程某应返还某商贸公司垫付款62000元。另，程某与余某的借款纠纷已另案调解结案（案号：（2023）皖0702民初5516号）。判决：一、被告某商贸公司应于2024年8月16日前向原告程某支付结算款436000元；二、第三人余某应于2024年8月16日前向原告程某支付结算款231000元；三、原告程某应于2024年9月30日前向被告某商贸公司支付垫付款62000元。"""

# V3-6 半角文号镜像陷阱：本案案号全角，送达回证编号半角；千分位金额
U043 = """承揽合同纠纷，案号（2023）湘1302民初221号（对应送达回证编号：(2023)湘1302民初221-1号）。查明：原告某门窗经营部为被告某置业公司加工安装门窗，合同价款884,440元，被告已付400,000元，尚欠484,440元。判决：被告某置业公司应于2024年1月15日前支付原告某门窗经营部剩余加工款484,440元（大写：肆拾捌万肆仟肆佰肆拾元整）。被告提出的产品质量异议因未在约定期限内书面提出，不予支持。本案诉讼保全费5000元由被告负担。"""

ITEMS = [
    ("u-038", U038, {"amount": 678500, "date": "2023-11-08", "case_no": "(2023)苏0582民初3364号"}, "civil_commercial"),
    ("u-039", U039, {"amount": 214930.5, "date": "2024-01-26", "case_no": "（2023）鲁0785民初2210号"}, "civil_commercial"),
    ("u-040", U040, {"amount": 976405.1, "date": "2024-06-30", "case_no": "（2022）豫0103民初8809号"}, "civil_commercial"),
    ("u-041", U041, {"amount": 203855.6, "date": "2024-04-06", "case_no": "(2023)冀0228民初4402号"}, "civil_commercial"),
    ("u-042", U042, {"amount": 436000, "date": "2024-08-16", "case_no": "（2023）皖0702民初5517号"}, "civil_commercial"),
    ("u-043", U043, {"amount": 484440, "date": "2024-01-15", "case_no": "（2023）湘1302民初221号"}, "civil_commercial"),
]


def main() -> int:
    existing = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
    have = {it["id"] for it in existing}
    if "u-038" in have:
        print("skip: u-038 已存在")
        return 0
    rows = []
    for iid, text, gold, domain in ITEMS:
        row = dict(_COMMON)
        row["id"] = iid
        row["domain"] = domain
        row["input"] = text
        row["gold"] = gold
        row["canary"] = f"CNJB-CANARY-{hashlib.sha256(iid.encode()).hexdigest()[:8]}"
        rows.append(row)
    lines = [l for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
    lines.extend(json.dumps(r, ensure_ascii=False) for r in rows)
    DATA.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"appended {len(rows)} items -> {len(lines)} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""R25：a_irac_reason 真难题第二批——要素不点名事实链（ah-101..104）。

E12 负结果：点名构成要件的复合题对头部模型饱和（ah-001..006 全 100）。
本批改为题面不出现考点术语、由事实链隐含争点：人身伤害免责条款
（506①，题面只给"概不负责"抗辩）、违约金低于损失的增加/赔偿双解
（585② acc 583）、特定日期目的不达的法定解除（563①(四)）、民间借贷
利率上限的新旧版本选择（民间借贷规定第25条，合同订立于2020-08-20后
→ 四倍LPR 规则）。全部锚文已逐字核对入库文本（夜间纪律：写 gold 前
逐字比对 lawkb/text/*.txt，仲裁条款独立性题因 567 实文不含"无效"情形
而放弃）。

用法::

    python scripts/add_airac_hard2_r25.py
"""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "public" / "a_irac_reason.jsonl"

CC = "中华人民共和国民法典"
LENDING = "最高人民法院关于审理民间借贷案件适用法律若干问题的规定"


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
    _item(100,
        "ah-101", "civil_commercial",
        "争点：某健身会所入会合同第8条印有'会员在训练中发生任何人身损害，本会所概不负责'。"
        "会员在私教课上因教练错误示范摔倒致手腕骨折，依合同起诉会所索赔；会所援引第8条抗辩，"
        "并称会员签字时已确认知悉。会所的抗辩能否成立？请按 IRAC 回答。",
        "造成对方人身损害的免责条款的效力",
        CC, "506", "合同中造成对方人身损害的免责条款无效（第506条第1项），其无效不因会员"
        "签字确认而补正，亦与是否构成格式条款无关；教练系执行工作任务致害，第8条抗辩不成立，"
        "会所应承担赔偿责任。",
        [], "2021-01-01",
    ),
    _item(101,
        "ah-102", "civil_commercial",
        "争点：买卖合同约定'乙方任何一批货物迟延，应向甲方支付违约金5万元'。乙方迟延交付"
        "致甲方实际损失约20万元，甲方起诉请求乙方支付违约金5万元并赔偿其余损失15万元。"
        "甲方的请求有无法律依据？请按 IRAC 回答。",
        "约定违约金低于损失时的增加请求与损失赔偿",
        CC, "585", "约定的违约金低于造成的损失的，人民法院或仲裁机构可以根据当事人的请求"
        "予以增加（第585条第2款）；支付违约金不足以弥补全部损失的，就未获弥补的其他损失"
        "还可依第583条请求赔偿。甲方可主张违约金增加至与损失相当，其差额赔偿请求有依据。",
        [(CC, "583")], "2021-01-01",
    ),
    _item(102,
        "ah-103", "civil_commercial",
        "争点：甲向乙订购演出灯光设备并预付30%货款，订单注明'须于5月20日前送达某市体育馆，"
        "供6月1日演唱会使用'。乙5月28日才送达，演唱会已另租设备如期举办完毕。甲通知乙"
        "解除订单、拒付余款并请求返还已付货款。甲的上述请求有无法律依据？请按 IRAC 回答。",
        "迟延履行致使合同目的不能实现的法定解除权",
        CC, "563", "订单交付期限与特定日期演出强绑定，乙迟延8日致合同目的不能实现，构成"
        "第563条第1款第4项法定解除事由；解除通知到达乙时合同解除，甲可拒付余款、请求返还"
        "已付货款并就损失求偿。",
        [], "2021-01-01",
    ),
    _item(103,
        "ah-104", "civil_commercial",
        "争点：2020年9月10日订立的民间借贷合同约定年利率18%，出借人已足额放款。借款人到期"
        "未还，出借人2024年起诉，请求按约定的年利率18%全额支付借期内利息。该请求能否全额"
        "支持？请按 IRAC 回答并给出规范依据。",
        "民间借贷利率司法保护上限的规范版本选择",
        LENDING, "25", "2020年8月20日后受理的案件适用修正后的民间借贷规定：利率保护上限为"
        "合同成立时一年期贷款市场报价利率的四倍（该时点约15.4%）。约定年利率18%超出上限，"
        "超出部分不受保护，按18%全额支持的请求不能成立。",
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

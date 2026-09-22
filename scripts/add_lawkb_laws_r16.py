"""R16：lawkb 增补 5 部法律（a_irac 金样条号修正的配套法条库扩充）。

背景：a_irac 19 题中约 10 题 gold 主条号有误（如未签劳动合同双倍工资挂在
民法典509，正确是劳动合同法82）。修正条号前必须先让 lawkb 收录对应法律，
否则 statute 谓词的 anchor 别名解析不到（alias miss → 永远 miss_retrieve）。

新增（全部为公开法律文本节录，入库依据见 docs/calc-real-model-report.md）：
- 民法总则 188（2017-10-01 施行，2021-01-01 随民法典施行废止 → effective_to）
- 民事诉讼法 35（协议管辖，2021 修正后编号）、234（案外人执行异议）
- 劳动合同法 82（未签书面合同双倍工资）
- 著作权法 54（侵权赔偿计算，2020 修正后编号）
- 行政诉讼法 12（受案范围节录）、78（行政协议履行与赔偿）

用法::

    python scripts/add_lawkb_laws_r16.py
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "lawkb"

LAWS: list[dict] = [
    {
        "file": "npc_general_principles.yaml",
        "law": {
            "law_id": "npc_general_principles",
            "names": ["中华人民共和国民法总则", "民法总则"],
            "level": "law",
            "promulgated_on": "2017-03-15",
            "abolished_on": "2021-01-01",
        },
        "articles": [
            {
                "article_no": "188",
                "version_id": "gp_188_2017",
                "effective_from": "2017-10-01",
                "effective_to": "2021-01-01",
                "superseded_by": "pc_188_2020",
                "note": "第一百八十八条（普通诉讼时效三年；与民法典188条同文）",
                "text": "向人民法院请求保护民事权利的诉讼时效期间为三年。法律另有规定的，依照其规定。"
                        "诉讼时效期间自权利人知道或者应当知道权利受到损害以及义务人之日起计算。"
                        "法律另有规定的，依照其规定。但是，自权利受到损害之日起超过二十年的，"
                        "人民法院不予保护；有特殊情况的，人民法院可以根据权利人的申请决定延长。",
            },
        ],
    },
    {
        "file": "npc_civil_procedure.yaml",
        "law": {
            "law_id": "npc_civil_procedure",
            "names": ["中华人民共和国民事诉讼法", "民事诉讼法"],
            "level": "law",
            "promulgated_on": "1991-04-09",
        },
        "articles": [
            {
                "article_no": "35",
                "version_id": "cproc_35_2021",
                "effective_from": "2022-01-01",
                "note": "第三十五条（协议管辖；2021年修正后编号，原2017版为第三十四条）",
                "text": "合同或者其他财产权益纠纷的当事人可以书面协议选择被告住所地、合同履行地、"
                        "合同签订地、原告住所地、标的物所在地等与争议有实际联系的地点的人民法院管辖，"
                        "但不得违反本法对级别管辖和专属管辖的规定。",
            },
            {
                "article_no": "234",
                "version_id": "cproc_234_2021",
                "effective_from": "2022-01-01",
                "note": "第二百三十四条（案外人执行异议；2021年修正后编号，原2017版为第二百二十七条）",
                "text": "执行过程中，案外人对执行标的提出书面异议的，人民法院应当自收到书面异议之日起"
                        "十五日内审查，理由成立的，裁定中止对该标的的执行；理由不成立的，裁定驳回。"
                        "案外人、当事人对裁定不服，认为原判决、裁定错误的，依照审判监督程序办理；"
                        "与原判决、裁定无关的，可以自裁定送达之日起十五日内向人民法院提起诉讼。",
            },
        ],
    },
    {
        "file": "npc_labor_contract.yaml",
        "law": {
            "law_id": "npc_labor_contract",
            "names": ["中华人民共和国劳动合同法", "劳动合同法"],
            "level": "law",
            "promulgated_on": "2007-06-29",
        },
        "articles": [
            {
                "article_no": "82",
                "version_id": "lc_82_2008",
                "effective_from": "2008-01-01",
                "note": "第八十二条（未签书面劳动合同的二倍工资）",
                "text": "用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，"
                        "应当向劳动者每月支付二倍的工资。用人单位违反本法规定不与劳动者订立"
                        "无固定期限劳动合同的，自应当订立无固定期限劳动合同之日起向劳动者每月"
                        "支付二倍的工资。",
            },
        ],
    },
    {
        "file": "npc_copyright.yaml",
        "law": {
            "law_id": "npc_copyright",
            "names": ["中华人民共和国著作权法", "著作权法"],
            "level": "law",
            "promulgated_on": "1990-09-07",
        },
        "articles": [
            {
                "article_no": "54",
                "version_id": "cr_54_2020",
                "effective_from": "2021-06-01",
                "note": "第五十四条（侵权赔偿计算；2020年修正后编号，原2010版为第四十九条）",
                "text": "侵犯著作权或者与著作权有关的权利的，侵权人应当按照权利人因此受到的实际损失"
                        "或者侵权人的违法所得给予赔偿；权利人的实际损失或者侵权人的违法所得难以计算的，"
                        "可以参照该权利使用费给予赔偿。对故意侵犯著作权或者与著作权有关的权利，"
                        "情节严重的，可以在按照上述方法确定数额的一倍以上五倍以下给予赔偿。"
                        "权利人的实际损失、侵权人的违法所得、权利使用费难以计算的，由人民法院根据"
                        "侵权行为的情节，判决给予五百元以上五百万元以下的赔偿。",
            },
        ],
    },
    {
        "file": "npc_admin_litigation.yaml",
        "law": {
            "law_id": "npc_admin_litigation",
            "names": ["中华人民共和国行政诉讼法", "行政诉讼法"],
            "level": "law",
            "promulgated_on": "1989-04-04",
        },
        "articles": [
            {
                "article_no": "12",
                "version_id": "al_12_2015",
                "effective_from": "2015-05-01",
                "note": "第十二条（受案范围节录：第一款第十一项行政协议）",
                "text": "人民法院受理公民、法人或者其他组织提起的下列诉讼：……（十一）认为行政机关"
                        "不依法履行、未按照约定履行或者违法变更、解除政府特许经营协议、土地房屋征收"
                        "补偿协议等协议的；……",
            },
            {
                "article_no": "78",
                "version_id": "al_78_2015",
                "effective_from": "2015-05-01",
                "note": "第七十八条（行政协议不履行/违法变更解除的责任）",
                "text": "被告不依法履行、未按照约定履行或者违法变更、解除本法第十二条第一款第十一项"
                        "规定的协议的，人民法院判决被告承担继续履行、采取补救措施或者赔偿损失等责任。"
                        "被告变更、解除本法第十二条第一款第十一项规定的协议合法，但未依法给予补偿的，"
                        "人民法院判决给予补偿。",
            },
        ],
    },
    {
        # R18：lh-06 继承纠纷（as_of=2020-06-01）金样修正配套——当时有效规范
        "file": "npc_succession_law.yaml",
        "law": {
            "law_id": "npc_succession_law",
            "names": ["中华人民共和国继承法", "继承法"],
            "level": "law",
            "promulgated_on": "1985-04-10",
            "abolished_on": "2021-01-01",
        },
        "articles": [
            {
                "article_no": "10",
                "version_id": "suc_10_1985",
                "effective_from": "1985-10-01",
                "effective_to": "2021-01-01",
                "superseded_by": "pc_1127_2020",
                "note": "第十条（法定继承顺序；2021-01-01 随民法典施行废止）",
                "text": "遗产按照下列顺序继承：第一顺序：配偶、子女、父母。第二顺序：兄弟姐妹、"
                        "祖父母、外祖父母。继承开始后，由第一顺序继承人继承，第二顺序继承人不继承。"
                        "没有第一顺序继承人继承的，由第二顺序继承人继承。",
            },
        ],
    },
]


# 民法典补录：a_irac 修正后的 gold/law_anchors/acceptable_articles 所涉条文，
# 均为公开文本节录。anchor 指向未入库条文时 statute 三检必败（exists=False），
# 因此 anchor 覆盖到的每一条都必须在库。
CIVIL_CODE_APPEND: list[dict] = [
    {"article_no": "469", "version_id": "pc_469_2020", "effective_from": "2021-01-01",
     "note": "第四百六十九条（合同形式：书面/口头/其他）",
     "text": "当事人订立合同，可以采用书面形式、口头形式或者其他形式。书面形式是合同书、信件、"
             "电报、电传、传真等可以有形地表现所载内容的形式。以电子数据交换、电子邮件等方式"
             "能够有形地表现所载内容，并可以随时调取查用的数据电文，视为书面形式。"},
    {"article_no": "506", "version_id": "pc_506_2020", "effective_from": "2021-01-01",
     "note": "第五百零六条（免责条款无效情形）",
     "text": "合同中的下列免责条款无效：（一）造成对方人身损害的；（二）因故意或者重大过失"
             "造成对方财产损失的。"},
    {"article_no": "525", "version_id": "pc_525_2020", "effective_from": "2021-01-01",
     "note": "第五百二十五条（同时履行抗辩权）",
     "text": "当事人互负债务，没有先后履行顺序的，应当同时履行。一方在对方履行之前有权拒绝"
             "其履行请求。一方在对方履行债务不符合约定时，有权拒绝其相应的履行请求。"},
    {"article_no": "526", "version_id": "pc_526_2020", "effective_from": "2021-01-01",
     "note": "第五百二十六条（后履行抗辩权）",
     "text": "当事人互负债务，有先后履行顺序，应当先履行债务一方未履行的，后履行一方有权拒绝"
             "其履行请求。应当先履行债务的当事人有确切证据证明对方有下列情形之一的，可以中止"
             "履行：（一）经营状况严重恶化；（二）转移财产、抽逃资金，以逃避债务；（三）丧失"
             "商业信誉；（四）有丧失或者可能丧失履行债务能力的其他情形。当事人没有确切证据"
             "中止履行的，应当承担违约责任。"},
    {"article_no": "566", "version_id": "pc_566_2020", "effective_from": "2021-01-01",
     "note": "第五百六十六条（合同解除的后果）",
     "text": "合同解除后，尚未履行的，终止履行；已经履行的，根据履行情况和合同性质，当事人"
             "可以请求恢复原状或者采取其他补救措施，并有权请求赔偿损失。合同因违约解除的，"
             "解除权人可以请求违约方承担违约责任，但是当事人另有约定的除外。"},
    {"article_no": "567", "version_id": "pc_567_2020", "effective_from": "2021-01-01",
     "note": "第五百六十七条（结算和清理条款的独立性）",
     "text": "合同的权利义务关系终止，不影响合同中结算和清理条款的效力。"},
    {"article_no": "583", "version_id": "pc_583_2020", "effective_from": "2021-01-01",
     "note": "第五百八十三条（履行/补救后的损失赔偿）",
     "text": "当事人一方不履行合同义务或者履行合同义务不符合约定的，在履行义务或者采取补救"
             "措施后，对方还有其他损失的，应当赔偿损失。"},
    {"article_no": "584", "version_id": "pc_584_2020", "effective_from": "2021-01-01",
     "note": "第五百八十四条（损失赔偿范围与可预见规则）",
     "text": "当事人一方不履行合同义务或者履行合同义务不符合约定，造成对方损失的，损失赔偿额"
             "应当相当于因违约所造成的损失，包括合同履行后可以获得的利益；但是，不得超过违约一方"
             "订立合同时预见到或者应当预见到的因违约可能造成的损失。"},
    {"article_no": "585", "version_id": "pc_585_2020", "effective_from": "2021-01-01",
     "note": "第五百八十五条（违约金及其调整）",
     "text": "当事人可以约定一方违约时应当根据违约情况向对方支付一定数额的违约金，也可以约定"
             "因违约产生的损失赔偿额的计算方法。约定的违约金低于造成的损失的，人民法院或者仲裁"
             "机构可以根据当事人的请求予以增加；约定的违约金过分高于造成的损失的，人民法院或者"
             "仲裁机构可以根据当事人的请求予以适当减少。当事人就迟延履行约定违约金的，违约方"
             "支付违约金后，还应当履行债务。"},
    {"article_no": "599", "version_id": "pc_599_2020", "effective_from": "2021-01-01",
     "note": "第五百九十九条（出卖人交付有关单证和资料义务）",
     "text": "出卖人应当按照约定或者交易习惯向买受人交付提取标的物单证以外的有关单证和资料。"},
    {"article_no": "675", "version_id": "pc_675_2020", "effective_from": "2021-01-01",
     "note": "第六百七十五条（借款期限与返还）",
     "text": "借款人应当按照约定的期限返还借款。对借款期限没有约定或者约定不明确，依据本法"
             "第五百一十条的规定仍不能确定的，借款人可以随时返还；贷款人可以催告借款人在合理"
             "期限内返还。"},
    {"article_no": "676", "version_id": "pc_676_2020", "effective_from": "2021-01-01",
     "note": "第六百七十六条（逾期利息）",
     "text": "借款人未按照约定的期限返还借款的，应当按照约定或者国家有关规定支付逾期利息。"},
    {"article_no": "1085", "version_id": "pc_1085_2020", "effective_from": "2021-01-01",
     "note": "第一千零八十五条（离婚后子女抚养费）",
     "text": "离婚后，子女由一方直接抚养的，另一方应当负担部分或者全部抚养费。负担费用的多少"
             "和期限的长短，由双方协议；协议不成的，由人民法院判决。前款规定的协议或者判决，"
             "不妨碍子女在必要时向父母任何一方提出超过协议或者判决原定数额的合理要求。"},
    # ---- R17 a_irac hard 子集配套条文 ----
    {"article_no": "172", "version_id": "pc_172_2020", "effective_from": "2021-01-01",
     "note": "第一百七十二条（表见代理）",
     "text": "行为人没有代理权、超越代理权或者代理权终止后，仍然实施代理行为，相对人有理由"
             "相信行为人有代理权的，代理行为有效。"},
    {"article_no": "186", "version_id": "pc_186_2020", "effective_from": "2021-01-01",
     "note": "第一百八十六条（违约责任与侵权责任竞合）",
     "text": "因当事人一方的违约行为，损害对方人身权益、财产权益的，受损害方有权选择请求"
             "其承担违约责任或者侵权责任。"},
    {"article_no": "504", "version_id": "pc_504_2020", "effective_from": "2021-01-01",
     "note": "第五百零四条（越权代表）",
     "text": "法人的法定代表人或者非法人组织的负责人超越权限订立的合同，除相对人知道或者"
             "应当知道其超越权限外，该代表行为有效，订立的合同对法人或者非法人组织发生效力。"},
    {"article_no": "588", "version_id": "pc_588_2020", "effective_from": "2021-01-01",
     "note": "第五百八十八条（违约金与定金选择适用）",
     "text": "当事人既约定违约金，又约定定金的，一方违约时，对方可以选择适用违约金或者"
             "定金条款。定金不足以弥补一方违约造成的损失的，对方可以请求赔偿超过定金数额"
             "的损失。"},
    {"article_no": "590", "version_id": "pc_590_2020", "effective_from": "2021-01-01",
     "note": "第五百九十条（不可抗力）",
     "text": "当事人一方因不可抗力不能履行合同的，根据不可抗力的影响，部分或者全部免除责任，"
             "但是法律另有规定的除外。因不可抗力不能履行合同的，应当及时通知对方，以减轻可能"
             "给对方造成的损失，并应当在合理期限内提供证明。当事人迟延履行后发生不可抗力的，"
             "不免除其违约责任。"},
    {"article_no": "692", "version_id": "pc_692_2020", "effective_from": "2021-01-01",
     "note": "第六百九十二条（保证期间，节录第一款）",
     "text": "保证期间是确定保证人承担保证责任的期间，不发生中止、中断和延长。"},
    {"article_no": "693", "version_id": "pc_693_2020", "effective_from": "2021-01-01",
     "note": "第六百九十三条（保证期间经过的责任免除）",
     "text": "一般保证的债权人未在保证期间对债务人提起诉讼或者申请仲裁的，保证人不再承担"
             "保证责任。连带责任保证的债权人未在保证期间请求保证人承担保证责任的，保证人"
             "不再承担保证责任。"},
    {"article_no": "807", "version_id": "pc_807_2020", "effective_from": "2021-01-01",
     "note": "第八百零七条（建设工程价款优先受偿权）",
     "text": "发包人未按照约定支付价款的，承包人可以催告发包人在合理期限内支付价款。"
             "发包人逾期不支付的，除根据建设工程的性质不宜折价、拍卖外，承包人可以与发包人"
             "协议将该工程折价，也可以请求人民法院将该工程依法拍卖。建设工程的价款就该工程"
             "折价或者拍卖的价款优先受偿。"},
    {"article_no": "1202", "version_id": "pc_1202_2020", "effective_from": "2021-01-01",
     "note": "第一千二百零二条（产品生产者侵权责任）",
     "text": "因产品存在缺陷造成他人损害的，生产者应当承担侵权责任。"},
    # ---- R18 lh-06 配套：民法典继承编法定继承顺序（继承法10的承替条文）----
    {"article_no": "1127", "version_id": "pc_1127_2020", "effective_from": "2021-01-01",
     "note": "第一千一百二十七条（法定继承顺序，节录前两款）",
     "text": "遗产按照下列顺序继承：（一）第一顺序：配偶、子女、父母；（二）第二顺序："
             "兄弟姐妹、祖父母、外祖父母。继承开始后，由第一顺序继承人继承，第二顺序继承人"
             "不继承；没有第一顺序继承人继承的，由第二顺序继承人继承。"},
]


def append_civil_code(created: list[str]) -> None:
    """向 npc_civil_code.yaml 幂等补录条文（按 version_id 查重）。"""
    import yaml

    ypath = ROOT / "laws" / "npc_civil_code.yaml"
    raw = yaml.safe_load(ypath.read_text(encoding="utf-8"))
    existing = {v["version_id"] for v in raw["article_version"]}
    for art in CIVIL_CODE_APPEND:
        if art["version_id"] in existing:
            print(f"skip（已存在）: {art['version_id']}")
            continue
        ref = f"text/{art['version_id']}.txt"
        tpath = ROOT / ref
        if not tpath.is_file():
            tpath.write_text(art["text"], encoding="utf-8")
        h = "sha256:" + hashlib.sha256(tpath.read_bytes()).hexdigest()
        raw["article_version"].append({
            "law_id": "npc_civil_code",
            "article_no": art["article_no"],
            "version_id": art["version_id"],
            "effective_from": art["effective_from"],
            "effective_to": None,
            "superseded_by": None,
            "note": art["note"],
            "text_hash": h,
            "text_ref": ref,
        })
        created.append(ref)
        print(f"appended: {art['version_id']}")
    # 与库内既有文件同为 yaml.safe_load 输出的排序风格（article_version 块字段顺序按 schema 排）
    ypath.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def main() -> int:
    text_dir = ROOT / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    append_civil_code(created)
    for spec in LAWS:
        ypath = ROOT / "laws" / spec["file"]
        if ypath.is_file():
            print(f"skip（已存在）: {ypath}")
            continue
        lines: list[str] = []
        meta = spec["law"]
        lines.append("law:")
        lines.append(f"  law_id: {meta['law_id']}")
        lines.append("  names:")
        for n in meta["names"]:
            lines.append(f"  - {n}")
        lines.append("  level: law")
        lines.append(f"  promulgated_on: '{meta['promulgated_on']}'")
        if meta.get("abolished_on"):
            lines.append(f"  abolished_on: '{meta['abolished_on']}'")
        lines.append("article_version:")
        for art in spec["articles"]:
            ref = f"text/{art['version_id']}.txt"
            tpath = ROOT / ref
            if tpath.is_file():
                print(f"skip（已存在）: {tpath}")
            else:
                tpath.write_text(art["text"], encoding="utf-8")
            h = "sha256:" + hashlib.sha256(tpath.read_bytes()).hexdigest()
            eff_to = art.get("effective_to")
            eff_to_s = f"'{eff_to}'" if eff_to else "null"
            sup = art.get("superseded_by") or "null"
            lines.append(f"- law_id: {meta['law_id']}")
            lines.append(f"  article_no: '{art['article_no']}'")
            lines.append(f"  version_id: {art['version_id']}")
            lines.append(f"  effective_from: '{art['effective_from']}'")
            lines.append(f"  effective_to: {eff_to_s}")
            lines.append(f"  superseded_by: {sup}")
            lines.append(f"  note: {art['note']}")
            lines.append(f"  text_hash: {h}")
            lines.append(f"  text_ref: {ref}")
            created.append(ref)
        ypath.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote: {ypath}")
    # 完整性把关：装载即校验（VERSION/hash/别名冲突/废止窗口）
    from cnjudbench.lawkb.store import LawkbStore

    store = LawkbStore.load(ROOT)
    print(f"store ok: {store.store_version}, laws={len(store.laws)}, versions={len(store.versions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

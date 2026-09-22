"""R16：a_irac_reason 19 题 gold 条号逐题修正 + acceptable_articles 多解口径。

审计背景（docs/calc-real-model-report.md §C2）：生成期「独立计算」≠ 语义正确。
v0.4 首批 19 题中约 10 题 gold 主条号挂错（如未签书面劳动合同双倍工资挂
民法典509，正确是劳动合同法82）——真实考生引用更专业的正确条号反被判 0。

修正原则：
- gold.rule_law / rule_article / citations / item.law_anchors 改为该争点下
  「最精确、as_of 时点现行有效」的主条号；
- gold.acceptable_articles 记录同争点下同样专业可接受的替代条号（any-of
  口径，由 ftp 的 article_set / statute 谓词消费；缺省时行为不变）；
- a-010 为时效陷阱题：as_of=2020-06-01 时民法典未施行，主条号应为
  民法总则188（民法典188 在该时点未生效，statute 三检会判 stale）。

用法::

    python scripts/fix_airac_golds_r16.py
"""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "public" / "a_irac_reason.jsonl"

CC = "中华人民共和国民法典"

# id → (rule_law, rule_article, [acceptable (law, article)...], effective_on)
# None 表示该题保持原样（金样本就正确）。
FIXES: dict[str, tuple | None] = {
    # 逾期还款：577 一般违约责任可接受；考生引借款章 675/676 更精确，纳入多解
    "a-001": (None, None, [(CC, "675"), (CC, "676")], None),
    "a-002": None,  # 诉讼时效 188 ✓
    "a-003": None,  # 盗窃 刑法264 ✓
    "a-004": None,  # 迟延履行解除 563 ✓
    # 可得利益：应为 584（赔偿范围+可预见规则），577 只是一般违约条款
    "a-005": (CC, "584", [(CC, "583")], "2021-01-01"),
    # 未开票抗辩拒付：对价关系 → 同时履行抗辩权 525；后履行抗辩权 526（先票后款
    # 约定下的拒付路径，R20 k=3 实测考生引 526 被误判 0 后补入）、509/599 亦可接受
    "a-006": (CC, "525", [(CC, "509"), (CC, "599"), (CC, "526")], "2021-01-01"),
    "a-007": None,  # 免责条款 506 ✓
    "a-008": None,  # 拒答题，无条件号
    "a-009": None,  # 违约金调整 585 ✓
    # 2020 时效陷阱：民法典 2021-01-01 才施行，应引民法总则 188
    "a-010": ("中华人民共和国民法总则", "188", [], "2017-10-01"),
    # 违约请求全额获赔：577 成立；584 赔偿范围/可预见同为正解
    "a-011": (None, None, [(CC, "584")], None),
    # 协议管辖：民诉法 35（2021 修正后编号；as_of=2024 现行）
    "a-012": ("中华人民共和国民事诉讼法", "35", [], "2022-01-01"),
    # 口头合同效力：民法典 469（合同形式）
    "a-013": (CC, "469", [], "2021-01-01"),
    # 解除后违约金条款：566（解除后果）；567 清理条款独立性、577 亦可接受
    "a-014": (CC, "566", [(CC, "567"), (CC, "577")], "2021-01-01"),
    # 未签书面合同双倍工资：劳动合同法 82（民法典 509 完全不对口）
    "a-015": ("中华人民共和国劳动合同法", "82", [], "2008-01-01"),
    # 抚养费放弃后变更：民法典 1085（抚养费）
    "a-016": (CC, "1085", [], "2021-01-01"),
    # 软件侵权赔偿计算：著作权法 54（2020 修正后编号）
    "a-017": ("中华人民共和国著作权法", "54", [], "2021-06-01"),
    # 行政协议赔偿：行政诉讼法 78；12 条受案范围、行政协议规定 19 条亦可接受
    "a-018": ("中华人民共和国行政诉讼法", "78", [
        ("中华人民共和国行政诉讼法", "12"),
        ("最高人民法院关于审理行政协议案件若干问题的规定", "19"),
    ], "2015-05-01"),
    # 排除执行权益（案外人执行异议）：民诉法 234（2021 修正后编号）；
    # 最高法执行异议复议规定 24/28/29 是认定标准的实体规范（专业替代解，
    # 未入库 → 仅 field 路径 any-of，statute 不验其别名）
    "a-019": ("中华人民共和国民事诉讼法", "234", [
        ("最高人民法院关于人民法院办理执行异议和复议案件若干问题的规定", "24"),
        ("最高人民法院关于人民法院办理执行异议和复议案件若干问题的规定", "28"),
        ("最高人民法院关于人民法院办理执行异议和复议案件若干问题的规定", "29"),
    ], "2022-01-01"),
}


def main() -> int:
    items = [json.loads(l) for l in PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = 0
    for it in items:
        fix = FIXES.get(it["id"])
        if fix is None:
            continue
        law, article, acceptable, eff = fix
        gold = it["gold"]
        if law is not None:
            gold["rule_law"] = law
            gold["rule_article"] = article
            gold["citations"] = [{"law": law, "article": article}]
            it["law_anchors"] = [{"law": law, "article": article, "effective_on": eff}]
        if acceptable:
            gold["acceptable_articles"] = [{"law": l, "article": a} for l, a in acceptable]
        changed += 1

    PATH.write_text(
        "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items),
        encoding="utf-8",
    )
    print(f"patched {changed}/{len(items)} items -> {PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""u_element_extract 干扰注入（DESIGN v0.4 §4.5 方案①/§5.1）。

对 19 题 input 追加一句「另案噪声」：≥2 个近形金额 + ≥1 个近形案号 + ≥1 个近形日期，
仅 gold 三要素满足谓词。注入确定性（由题号与 gold 派生，无随机），脚本留档可复现。

跑一次幂等性：按「已含标记 ‖」判断跳过。用法::

    python scripts/add_u_distractors.py            # 写入 data/public/u_element_extract.jsonl
    python scripts/add_u_distractors.py --check    # 只校验不写入
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ITEMS = REPO / "data" / "public" / "u_element_extract.jsonl"

MARK = "【另案信息】"


def _transpose_amount(a: int) -> int:
    """近形金额①：末两位对调（不足 100 或对调后相等则 ÷10）。"""
    s = str(a)
    if len(s) >= 3 and s[-1] != s[-2]:
        return int(s[:-2] + s[-1] + s[-2])
    return a // 10


def _second_amount(a: int, avoid: int) -> int:
    """近形金额②：×10，若与 gold/①撞车则逐次 ÷10 直到互异。"""
    cand = a * 10
    while cand in (a, avoid) or cand < 10:
        cand //= 10 if cand not in (a, avoid) else 1
        if cand in (a, avoid):
            cand = a + max(11, a // 100)
    return cand


def _case_variants(case_no: str) -> tuple[str, str]:
    """近形案号：①年份 −1；②末段数字最后一位 +1（循环）。"""
    m = re.search(r"（(\d{4})）", case_no)
    year = str(int(m.group(1)) - 1) if m else "2022"
    v1 = re.sub(r"（\d{4}）", f"（{year}）", case_no, count=1)
    m2 = re.search(r"(\d)(号?)$", case_no)
    if m2:
        tail = str((int(m2.group(1)) + 1) % 10)
        v2 = case_no[: -len(m2.group(0))] + tail + m2.group(2)
    else:
        v2 = v1 + "号"
    return v1, v2


_TEMPLATES = (
    "【另案信息】另查明，关联另案（案号：{dc2}）中同当事人被认定应付{da1}元，"
    "款项于{dd2}到期，另涉保证金{da2}元；该案与本案无关。",
    "【另案信息】附：当事人于另案（案号：{dc2}）主张借款{da1}元（约定{dd2}到期）"
    "及违约金{da2}元，均不属本案审理范围。",
    "【另案信息】核查发现另有生效判决（案号：{dc3}）确定同当事人支付{da1}元，"
    "履行期至{dd2}届满，其执行情况与本案无关；另案保证金{da2}元亦已另行处理。",
)


def build_input(item: dict) -> str:
    gold = item["gold"]
    amount = int(gold["amount"])
    da1 = _transpose_amount(amount)
    da2 = _second_amount(amount, da1)
    dc2, dc3 = _case_variants(str(gold["case_no"]))
    dd2 = (date.fromisoformat(gold["date"]) + timedelta(days=10)).isoformat()
    tpl = _TEMPLATES[int(item["id"].split("-")[1]) % len(_TEMPLATES)]
    return item["input"] + tpl.format(da1=da1, da2=da2, dc2=dc2, dc3=dc3, dd2=dd2)


def check_item(item: dict) -> list[str]:
    """溯源校验：剥离注入段后按确定性规则重建，须与现文逐字一致。"""
    errs: list[str] = []
    text = item["input"]
    gold = item["gold"]
    if text.count(MARK) != 1:
        return [f"标记数异常: {text.count(MARK)}"]
    base = text.split(MARK)[0]
    rebuilt = build_input({**item, "input": base})
    if rebuilt != text:
        errs.append("重建不一致（注入段与规则不符）")
    if str(gold["case_no"]) in text.split(MARK)[1]:
        errs.append("干扰案号与 gold 案号相同")
    a = int(gold["amount"])
    da1 = _transpose_amount(a)
    da2 = _second_amount(a, da1)
    if a in (da1, da2):
        errs.append("干扰金额与 gold 相同")
    if gold["date"] in text.split(MARK)[1]:
        errs.append("干扰日期与 gold 相同")
    return errs


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    items = [json.loads(l) for l in ITEMS.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    if args.check:
        bad = 0
        for it in items:
            errs = check_item(it)
            if errs:
                bad += 1
                print(f"{it['id']}: {'; '.join(errs)}")
        print("OK: 全部 19 题已注入且 gold 完整" if bad == 0 else f"FAIL: {bad} 题异常")
        return 1 if bad else 0

    out = []
    n_new = 0
    for it in items:
        if MARK not in it["input"]:
            it["input"] = build_input(it)
            n_new += 1
        out.append(json.dumps(it, ensure_ascii=False))
    ITEMS.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"注入完成：新注入 {n_new} 题（共 {len(items)} 题）→ {ITEMS}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

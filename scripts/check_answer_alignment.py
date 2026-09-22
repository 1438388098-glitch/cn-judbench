"""考生换答检测 guard：回灌前机检 answer↔item 对位（R21）。

背景（R14 a-010/a-011、R20 a-001/a-002 两次实测事故）：subagent 考生按
落盘协议写答案时偶发把答案写错文件位——答案与题面错位直接污染题分与
flip 统计，且人工抽查难以发现。

方法：对每个 item 取题面 input 的字符 bigram 集合，与 run 目录下每份答案
全文的 bigram 集合算 Dice 系数。若「别人的答案对本题的相似度」显著高于
「自己的答案」（own + margin 仍低于 best_other），判为换答嫌疑。

用法::

    python scripts/check_answer_alignment.py --run-dir runs/airac-k3-run3
    python scripts/check_answer_alignment.py --run-dir runs/x --margin 0.5 --json out.json

退出码：0 = 无嫌疑；1 = 存在换答嫌疑（CI 中应阻断回灌）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bigrams(text: str) -> set[str]:
    t = "".join(ch for ch in text if not ch.isspace())
    return {t[i : i + 2] for i in range(len(t) - 1)}


def _dice(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


def main() -> int:
    ap = argparse.ArgumentParser(description="考生换答检测（answer↔item 对位）")
    ap.add_argument("--run-dir", required=True, help="含 prompts/ index.json answers/ 的 run 目录")
    ap.add_argument("--margin", type=float, default=0.05,
                    help="best_other 超出 own 至少多少才算嫌疑（缺省 0.05，差分 Dice）")
    ap.add_argument("--json", dest="json_out", default=None, help="明细写出路径")
    args = ap.parse_args()

    run = Path(args.run_dir)
    index_path = run / "index.json"
    if not index_path.is_file():
        print(f"FAIL: 缺 {index_path}（run 目录需先经 export_prompts.py 导出）")
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))
    answers: dict[str, str] = {}
    for entry in index:
        apath = run / entry["answer_file"]
        answers[entry["item_id"]] = apath.read_text(encoding="utf-8") if apath.is_file() else ""
    ans_grams = {k: _bigrams(v) for k, v in answers.items()}

    # 差分信号：扣掉「多数 prompt/答案共有的模板 bigram」（schema 说明等），
    # 只留题面/答案的特异内容——否则全文相似度被模板淹没，换答不可分。
    def _common(gram_sets: list[set[str]], frac: float = 0.6) -> set[str]:
        if not gram_sets:
            return set()
        threshold = frac * len(gram_sets)
        counts: dict[str, int] = {}
        for g in gram_sets:
            for x in g:
                counts[x] = counts.get(x, 0) + 1
        return {x for x, c in counts.items() if c >= threshold}

    prompt_grams = {}
    for entry in index:
        prompt_grams[entry["item_id"]] = _bigrams(
            (run / entry["prompt_file"]).read_text(encoding="utf-8")
        )
    common_p = _common(list(prompt_grams.values()))
    common_a = _common(list(ans_grams.values()))
    p_spec = {k: v - common_p for k, v in prompt_grams.items()}
    a_spec = {k: v - common_a for k, v in ans_grams.items()}

    suspects = []
    for entry in index:
        iid = entry["item_id"]
        if not answers.get(iid):
            suspects.append({"item": iid, "kind": "missing", "detail": "答案文件缺失"})
            continue
        own = _dice(p_spec[iid], a_spec[iid])
        best_other, best_id = 0.0, None
        for oid, grams in a_spec.items():
            if oid == iid:
                continue
            d = _dice(p_spec[iid], grams)
            if d > best_other:
                best_other, best_id = d, oid
        if best_id is None or best_other <= own or best_other - own < args.margin:
            continue
        # 反向确认（互为最优 = 直接换答）：对方的 prompt 是否也更「亲」本题答案
        reverse = _dice(p_spec[best_id], a_spec[iid])
        reverse_own = _dice(p_spec[best_id], a_spec[best_id])
        suspects.append({
            "item": iid, "kind": "swap_suspect",
            "own": round(own, 3), "best_other": round(best_other, 3),
            "best_other_item": best_id,
            "reverse": round(reverse, 3), "reverse_own": round(reverse_own, 3),
            "mutual": bool(reverse > reverse_own),
            "detail": (f"{iid} 自己的答案相似度 {own:.2f} 低于 {best_id} 的 {best_other:.2f}"
                       f"（反向确认 {'成立' if reverse > reverse_own else '不成立'}）"),
        })

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(suspects, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if suspects:
        for s in suspects:
            print(f"SUSPECT [{s['kind']}] {s['detail']}")
        print(f"换答嫌疑 {len(suspects)} 项 -> 回灌阻断（先人工核对文件对位）")
        return 1
    print(f"对位检查通过：{len(index)} 份答案与题面均自洽")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

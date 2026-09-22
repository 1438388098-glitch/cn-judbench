# -*- coding: utf-8 -*-
"""pass^k 多 run 聚合（DESIGN v0.4 §6.2 正式口径）。

把同一模型同一配置的 k 个 run 目录聚合成组合语义 pass^k 报告：
- 通过 = 题分 ≥ threshold（缺省 100 满分通过；--threshold 60 视为解决）；
- pass^k = C(通过数, k) / C(n, k) 对题目集合求均值（cnjudbench.metrics.pass_power_k）；
- grand = pass^k 题均 ± bootstrap 95% CI（有放回抽题 1000 次，seed=42）；
- 逐题翻转率（§6.1 flip 门禁）：相邻 run 题分不同的题比例。

用法：
  python scripts/aggregate_passk.py --runs runs/dsA runs/dsB runs/dsC --out docs/passk-ds.md
  python scripts/aggregate_passk.py --runs runs/a runs/b --threshold 60
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from cnjudbench.metrics.cost import pass_power_k_per_item

THRESHOLD_DEFAULT = 100.0
N_BOOT = 1000
SEED = 42


def load_runs(runs: list[Path]) -> tuple[list[str], list[dict[str, float]]]:
    """读 k 个 run 的逐题分；返回 (全部题 id 并集, 每个 run 的 {id: score})。"""
    ids: list[str] = []
    per_run: list[dict[str, float]] = []
    for run in runs:
        summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
        scores: dict[str, float] = {}
        for task in summary.get("tasks", {}).values():
            for it in task.get("items", []):
                if it.get("score") in (None, "n/a"):
                    continue
                scores[it["id"]] = float(it["score"])
        if not scores:
            raise SystemExit(f"{run}: summary.json 无逐题分")
        per_run.append(scores)
        for iid in scores:
            if iid not in ids:
                ids.append(iid)
    return ids, per_run


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", nargs="+", required=True, type=Path,
                    help="同一模型 ≥2 个 run 目录（各含 summary.json）")
    ap.add_argument("--threshold", type=float, default=THRESHOLD_DEFAULT,
                    help="通过阈值（缺省 100=满分通过）")
    ap.add_argument("--k", type=int, default=None, help="pass^k 的 k（缺省 = run 数）")
    ap.add_argument("--out", type=Path, default=None, help="markdown 输出路径")
    args = ap.parse_args()

    k = args.k or len(args.runs)
    ids, per_run = load_runs(args.runs)
    flags = [[s.get(i, float("nan")) >= args.threshold for i in ids] for s in per_run]
    # 题目须在全部 run 中有分；缺失算未通过（保守）
    per_item_flags = [[f[j] for f in flags] for j in range(len(ids))]
    item_passk = pass_power_k_per_item(per_item_flags, k)
    # 试次 <k 被丢弃的题按 0 计入均值口径说明（此处 n 全等，仅防御）
    if len(item_passk) < len(ids):
        item_passk += [0.0] * (len(ids) - len(item_passk))
    grand = sum(item_passk) / len(item_passk) if item_passk else 0.0

    rng = random.Random(SEED)
    boots = []
    for _ in range(N_BOOT):
        idx = [rng.randrange(len(item_passk)) for _ in range(len(item_passk))]
        boots.append(sum(item_passk[j] for j in idx) / len(idx))
    boots.sort()
    lo, hi = boots[int(0.025 * N_BOOT)], boots[int(0.975 * N_BOOT) - 1]

    # flip：相邻 run 题分不同（共同题）
    flips = total = 0
    for a, b in zip(per_run, per_run[1:]):
        for i in ids:
            if i in a and i in b:
                total += 1
                flips += 1 if a[i] != b[i] else 0
    flip_rate = (flips / total) if total else None

    lines = [
        f"# pass^{k} 聚合报告（组合语义，DESIGN v0.4 §6.2）",
        "",
        f"- runs：{', '.join(str(r) for r in args.runs)}",
        f"- 通过阈值：≥{args.threshold:g}；n 题 = {len(ids)}；k = {k}"
        f"（题目在任一 run 缺分按未通过计，结果为保守下界）",
        f"- **grand pass^{k} = {100 * grand:.2f} "
        f"[{100 * lo:.2f}, {100 * hi:.2f}]**（bootstrap 95%，n={N_BOOT}，seed={SEED}）",
        (f"- 逐对题级翻转率 = {flips}/{total} = {100 * flip_rate:.1f}%"
         + ("（>5% 门禁：本组 run 不得进正式表）" if flip_rate and flip_rate > 0.05
            else "（≤5% 门禁内）")) if flip_rate is not None else "- 翻转率：run 不足",
        "",
        "| 题目 | " + " | ".join(f"run{j+1}" for j in range(len(per_run)))
        + f" | pass^{k} |",
        "|---|" + "---|" * (len(per_run) + 1),
    ]
    for j, iid in enumerate(ids):
        row_scores = " | ".join(
            f"{s.get(iid, float('nan')):.2f}" if iid in s else "n/a" for s in per_run)
        lines.append(f"| {iid} | {row_scores} | {100 * item_passk[j]:.2f} |")
    report = "\n".join(lines) + "\n"
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"written: {args.out}")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

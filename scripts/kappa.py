# -*- coding: utf-8 -*-
"""人评一致性计算（docs/human-eval-protocol.md §4）。

输入：双评者 CSV（列 item_id,rater1,rater2[,...]），输出
- 评者间 Cohen's weighted κ（二次权重，档位有序）+ bootstrap 95% CI（seed=42）；
- 人-机 Spearman ρ（可选 --machine CSV：item_id,machine_score）。

只算统计，不做判定；n<2 时诚实报 n/a。
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path


def _weighted_kappa(a: list[float], b: list[float], cats: list[float]) -> float:
    """Cohen's κ with quadratic weights on ordered categories."""
    n = len(a)
    k = len(cats)
    idx = {c: i for i, c in enumerate(cats)}
    O = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        O[idx[x]][idx[y]] += 1
    w = [[((i - j) / (k - 1)) ** 2 if k > 1 else 0.0 for j in range(k)] for i in range(k)]
    po = sum(O[i][j] * w[i][j] for i in range(k) for j in range(k)) / n
    ra = [sum(O[i][j] for j in range(k)) / n for i in range(k)]
    rb = [sum(O[i][j] for i in range(k)) / n for j in range(k)]
    pe = sum(w[i][j] * ra[i] * rb[j] for i in range(k) for j in range(k))
    return 1.0 - (po / pe) if pe > 0 else float("nan")


def inter_rater_kappa(pairs: list[tuple[float, float]], cats: list[float],
                      n_boot: int = 1000, seed: int = 42) -> dict:
    """weighted κ + bootstrap CI。pairs: [(rater1, rater2)…]"""
    if len(pairs) < 2:
        return {"kappa": None, "ci95_low": None, "ci95_high": None, "n": len(pairs)}
    a = [x for x, _ in pairs]
    b = [y for _, y in pairs]
    point = _weighted_kappa(a, b, cats)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        boots.append(_weighted_kappa([x for x, _ in sample], [y for _, y in sample], cats))
    boots = [v for v in boots if v == v]
    boots.sort()
    lo = boots[int(0.025 * (len(boots) - 1))] if boots else None
    hi = boots[int(0.975 * (len(boots) - 1))] if boots else None
    return {"kappa": round(point, 4), "ci95_low": None if lo is None else round(lo, 4),
            "ci95_high": None if hi is None else round(hi, 4),
            "n": len(pairs), "n_boot": n_boot, "seed": seed}


def spearman_rho(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    rank_map = lambda v: {val: r for r, val in enumerate(sorted(set(v)), 1)}  # noqa: E731
    rx = [rank_map(xs)[v] for v in xs]
    ry = [rank_map(ys)[v] for v in ys]
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 4) if den else None


def main() -> int:
    ap = argparse.ArgumentParser(description="双评者 weighted κ + 人-机 Spearman ρ")
    ap.add_argument("--ratings", required=True, help="CSV: item_id,rater1,rater2[,...]")
    ap.add_argument("--cats", default="0,1,2,3", help="有序档位，逗号分隔（默认 0,1,2,3）")
    ap.add_argument("--machine", default=None, help="CSV: item_id,machine_score（可选）")
    ap.add_argument("--out", default=None, help="结果 JSON 输出路径")
    args = ap.parse_args()

    rows = list(csv.DictReader(Path(args.ratings).read_text(encoding="utf-8-sig").splitlines()))
    cats = [float(c) for c in args.cats.split(",")]
    pairs = [(float(r["rater1"]), float(r["rater2"])) for r in rows
             if r.get("rater1") and r.get("rater2")]
    result = {"inter_rater": inter_rater_kappa(pairs, cats), "n_ratings": len(rows)}
    if args.machine:
        mach = {r["item_id"]: float(r["machine_score"]) for r in
                csv.DictReader(Path(args.machine).read_text(encoding="utf-8-sig").splitlines())}
        xs = [mach[r["item_id"]] for r in rows if r["item_id"] in mach]
        ys = [float(r["rater1"]) for r in rows if r["item_id"] in mach]
        result["human_vs_machine_spearman"] = spearman_rho(xs, ys)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""配对分差 bootstrap 95% CI（FRAMEWORK §0 / §8；单位：分）。"""

from __future__ import annotations

import random


def paired_bootstrap_ci(a: list[float], b: list[float], *, n_boot: int = 1000, seed: int = 42) -> dict:
    """同题配对分差 mean(a-b) 的 bootstrap 95% CI。"""
    if len(a) != len(b) or not a:
        raise ValueError("配对样本必须等长且非空")
    diffs = [x - y for x, y in zip(a, b)]
    rng = random.Random(seed)
    means: list[float] = []
    n = len(diffs)
    for _ in range(n_boot):
        s = 0.0
        for _i in range(n):
            s += diffs[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int(0.025 * (n_boot - 1))]
    hi = means[int(0.975 * (n_boot - 1))]
    point = sum(diffs) / n
    return {"point": point, "ci95_low": lo, "ci95_high": hi, "n": n, "seed": seed, "n_boot": n_boot}

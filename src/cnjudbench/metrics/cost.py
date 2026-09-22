"""稳定性与成本：pass^k · $/solve · p95 latency（FRAMEWORK §8）。"""

from __future__ import annotations


def pass_at_k(per_item_runs: list[list[bool]], k: int = 5) -> float:
    """同题 k 次全过比例；runs[i] 为第 i 题各次是否通过。"""
    if k <= 0:
        raise ValueError("k 必须 > 0")
    ok = 0
    for runs in per_item_runs:
        if len(runs) < k:
            continue
        if all(runs[:k]):
            ok += 1
    denom = sum(1 for r in per_item_runs if len(r) >= k) or 1
    return ok / denom


def dollar_per_solve(est_cost_usd: float, scores: list[float], threshold: float = 60.0) -> float | None:
    solved = sum(1 for s in scores if s >= threshold)
    if solved == 0:
        return None
    return est_cost_usd / solved


def p95_latency(latencies_ms: list[float]) -> float | None:
    if not latencies_ms:
        return None
    xs = sorted(latencies_ms)
    idx = min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))
    return xs[idx]

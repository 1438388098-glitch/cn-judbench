"""稳定性与成本：pass^k · $/solve · p95 latency（FRAMEWORK §8）。"""

from __future__ import annotations


def pass_at_k(per_item_runs: list[list[bool]], k: int = 5) -> float:
    """序列语义 pass^k（兼容口径）：同题前 k 次全过比例；runs[i] 为第 i 题各次是否通过。

    DESIGN v0.4 §6.2：序列语义仅限 stability 展示，**不进主表**；主表用
    :func:`pass_power_k`（组合语义）。
    """
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


def pass_power_k_per_item(per_item_runs: list[list[bool]], k: int = 3) -> list[float]:
    """组合语义 pass^k 的题级贡献明细：C(通过数, k) / C(n, k)。

    试次数 < k 的题不计入（返回列表短于输入）。
    """
    if k <= 0:
        raise ValueError("k 必须 > 0")
    from math import comb

    per_item: list[float] = []
    for runs in per_item_runs:
        n = len(runs)
        if n < k:
            continue
        c = sum(1 for x in runs if x)
        per_item.append(comb(c, k) / comb(n, k))
    return per_item


def pass_power_k(per_item_runs: list[list[bool]], k: int = 3) -> float | None:
    """组合语义 pass^k（DESIGN v0.4 §6.2 正式口径，主表用）。

    从每题 n(≥k) 次独立试次中**无放回任取** k 次均通过的概率：
    题级贡献 = C(通过数, k) / C(n, k)，整体取题间均值。

    c388：有题但全部试次不足 k = 不可测，返回 None（显示 n/a）——
    禁止把「没测成」报成 0.00 冒充全不稳定；空输入仍返回 0.0（既有金样）。
    """
    per_item = pass_power_k_per_item(per_item_runs, k)
    if not per_item:
        return 0.0 if not per_item_runs else None
    return sum(per_item) / len(per_item)


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

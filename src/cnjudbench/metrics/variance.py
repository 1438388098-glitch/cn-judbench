"""P3 稳健列：方差分解 · pass^k 双列 · score–time AUC（impl-P3 §5/§6）。"""

from __future__ import annotations

from ..metrics.cost import pass_power_k
from ..scale import fmt2


def pass_k_fixed_user(per_item_runs: list[list[bool]], k: int = 3) -> float:
    """固定 user_seed 的 pass^k：模型稳定度（组合语义，DESIGN §6.2 主表口径）。"""
    return pass_power_k(per_item_runs, k=k)


def pass_k_swapped_persona(per_item_runs: list[list[bool]], k: int = 3) -> float:
    """换 persona 种子的 pass^k：交互稳定度（组合语义，DESIGN §6.2 主表口径）。"""
    return pass_power_k(per_item_runs, k=k)


def _var(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def decompose_variance(
    *,
    model_scores: list[float] | None = None,
    user_scores: list[float] | None = None,
    judge_scores: list[float] | None = None,
) -> dict:
    """``total_var ≈ model_var + user_script_var + judge_var``（审查 #5）。

    各列为空时对应方差记 0，**禁止**把用户噪声记进 model_var。
    """
    model_var = _var(model_scores or [])
    user_var = _var(user_scores or [])
    judge_var = _var(judge_scores or [])
    total = model_var + user_var + judge_var
    return {
        "model_var": float(f"{model_var:.6f}"),
        "user_script_var": float(f"{user_var:.6f}"),
        "judge_var": float(f"{judge_var:.6f}"),
        "total_var": float(f"{total:.6f}"),
        "note": "user_script_var 不得并入模型账；律师基线缺失时写未测",
    }


def score_time_auc(points: list[tuple[float, float]]) -> float | None:
    """score–time 曲线 AUC 归一（L4）。

    points: [(t_norm∈[0,1], score_norm∈[0,1])…]，梯形积分后 ×100，两位小数由调用方 fmt2。
    """
    if not points:
        return None
    pts = sorted(points, key=lambda p: p[0])
    auc = 0.0
    for (t0, s0), (t1, s1) in zip(pts, pts[1:]):
        dt = max(0.0, t1 - t0)
        auc += dt * (s0 + s1) / 2.0
    # 时间轴不足 1.0 时按已覆盖区间归一，避免短任务被低估
    t_span = pts[-1][0] - pts[0][0] if len(pts) > 1 else 1.0
    if t_span <= 0:
        return 100.0 * pts[0][1]
    return 100.0 * (auc / t_span)


def format_stability(
    *,
    pass_k_model: float | None,
    pass_k_user: float | None,
    variance: dict,
    lawyer_baseline: str = "未测",
) -> dict:
    return {
        "pass_k_fixed_user_str": fmt2(100.0 * pass_k_model) if pass_k_model is not None else "n/a",
        "pass_k_swapped_persona_str": fmt2(100.0 * pass_k_user) if pass_k_user is not None else "n/a",
        "variance": variance,
        "lawyer_baseline": lawyer_baseline,
    }

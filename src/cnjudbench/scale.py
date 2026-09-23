"""百分制映射（FRAMEWORK §0 评分总则；P0b 执行器统一接用，禁止各任务私自换算）。

- 一切对外分数为 0.00–100.00、两位小数、ROUND_HALF_EVEN；
- 排序/聚合用未舍入值，展示用 :func:`fmt2`；
- 不可评为 ``None``（报表标 ``n/a``），禁止填 0.00 充数。
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

# over_refuse（应答而空拒）的能力分惩罚系数（DESIGN v0.4 §4.1 ②）。
# 集中定义：消融/敏感性分析改这里，调用点不许各写一个字面量。
OVER_REFUSE_PENALTY = 0.50


def to_percent_unit(x: float) -> float:
    """``acc/F1/EM/NDCG ∈ [0,1]`` → 百分制（×100）。"""
    if not 0.0 <= x <= 1.0:
        raise ValueError(f"to_percent_unit 输入必须在 [0,1]：{x}")
    return 100.0 * x


def to_percent_rubric(v: float, lo: float, hi: float) -> float:
    """rubric 原始刻度 ``v ∈ [lo, hi]`` → 百分制线性映射。"""
    if hi <= lo:
        raise ValueError(f"rubric 刻度非法：lo={lo}, hi={hi}")
    if not lo <= v <= hi:
        raise ValueError(f"rubric 取值越界：v={v} 不在 [{lo}, {hi}]")
    return 100.0 * (v - lo) / (hi - lo)


def gate_zero(_score: float = 0.0) -> float:
    """gate 触发（幻觉条文 / 危险承诺等一票否决）→ 0.00。"""
    return 0.0


def cap_at(score: float, cap: float = 50.0) -> float:
    """gate 封顶（如引用不达标）→ min(score, cap)。"""
    return min(score, cap)


def fmt2(x: float) -> str:
    """固定两位小数字符串（ROUND_HALF_EVEN），报表唯一出口。非有限值拒绝。"""
    d = Decimal(str(x))
    if not d.is_finite():
        raise ValueError(f"fmt2 仅接受有限数值：{x}")
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))

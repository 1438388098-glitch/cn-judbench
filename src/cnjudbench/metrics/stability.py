"""score–time 与 L4 稳健指标的辅助（挂在 variance 模块，便于 CLI/测试引用）。"""

from .variance import (
    decompose_variance,
    format_stability,
    pass_k_fixed_user,
    pass_k_swapped_persona,
    score_time_auc,
)

__all__ = [
    "decompose_variance",
    "format_stability",
    "pass_k_fixed_user",
    "pass_k_swapped_persona",
    "score_time_auc",
]

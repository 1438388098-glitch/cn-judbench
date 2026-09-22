"""P3：方差分解与 pass^k 双列（审查 #5）。"""

from __future__ import annotations

from cnjudbench.metrics.variance import (
    decompose_variance,
    format_stability,
    pass_k_fixed_user,
    pass_k_swapped_persona,
)


def test_decompose_variance_keeps_user_out_of_model():
    v = decompose_variance(model_scores=[80.0, 82.0], user_scores=[50.0, 90.0], judge_scores=[70.0, 70.0])
    assert v["user_script_var"] > 0
    assert v["judge_var"] == 0.0
    assert v["model_var"] < v["user_script_var"]
    assert abs(v["total_var"] - (v["model_var"] + v["user_script_var"] + v["judge_var"])) < 1e-6


def test_pass_k_dual_columns():
    runs = [[True, True, True], [True, False, True]]
    assert pass_k_fixed_user(runs, k=3) == 0.5
    assert pass_k_swapped_persona(runs, k=3) == 0.5


def test_format_stability_lawyer_baseline_unmeasured():
    out = format_stability(pass_k_model=1.0, pass_k_user=0.5,
                           variance=decompose_variance(model_scores=[1.0]),
                           lawyer_baseline="未测")
    assert out["lawyer_baseline"] == "未测"
    assert out["pass_k_fixed_user_str"] == "100.00"
    assert out["pass_k_swapped_persona_str"] == "50.00"

"""百分制映射单测：两位小数、ROUND_HALF_EVEN、gate/cap、范围校验。"""

import pytest

from cnjudbench.scale import cap_at, fmt2, gate_zero, to_percent_rubric, to_percent_unit


@pytest.mark.parametrize(
    "x,expect",
    [
        (2.675, "2.68"),  # half-even：恰好半分位时向偶数舍
        (2.685, "2.68"),
        (0.856, "0.86"),
        (85.4349, "85.43"),
        (99.995, "100.00"),
        (0, "0.00"),
        (100, "100.00"),
    ],
)
def test_fmt2_half_even(x, expect):
    assert fmt2(x) == expect


def test_to_percent_unit():
    assert to_percent_unit(0.8543) == pytest.approx(85.43)
    with pytest.raises(ValueError):
        to_percent_unit(1.2)
    with pytest.raises(ValueError):
        to_percent_unit(-0.1)


def test_to_percent_rubric():
    assert to_percent_rubric(2, 0, 4) == pytest.approx(50.0)  # 0–4 刻度 → ×25
    assert to_percent_rubric(3, 0, 5) == pytest.approx(60.0)  # 0–5 刻度 → ×20
    with pytest.raises(ValueError):
        to_percent_rubric(5, 0, 4)


def test_gates():
    assert gate_zero(87.65) == 0.0
    assert cap_at(87.65) == 50.0
    assert cap_at(23.45) == 23.45

"""隐藏单测：ci-008（单利利息，本金 1500000 元，年利率 7.0%，120 天）。"""

_EXPECTED = 34520.55  # 本金×年利率×天数/365，分位四舍五入（生成期独立计算）
_FORMULA_ID = "simple_interest_365"


def _close(got, want) -> bool:
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
    return abs(g - _EXPECTED) <= 0.01 or abs(g - _EXPECTED) <= 0.005 * _EXPECTED


def check(answer: dict) -> tuple[int, int]:
    passed = 0
    total = 2
    if _close(answer.get("answer"), _EXPECTED):
        passed += 1
    work = answer.get("work") or dict()
    if isinstance(work, dict) and str(work.get("formula_id", "")).strip() == _FORMULA_ID:
        passed += 1
    return passed, total

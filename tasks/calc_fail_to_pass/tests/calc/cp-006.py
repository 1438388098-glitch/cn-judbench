"""隐藏单测：cp-006（期间计算，自 2024-03-11 起算 60 日，起算日不计入）。"""

_EXPECTED_DAYS = 60  # 届满日 - 开始日的自然日差（生成期独立计算）
_FORMULA_ID = "period_days"


def _close(got, want) -> bool:
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
    return abs(g - _EXPECTED_DAYS) <= 0.01


def check(answer: dict) -> tuple[int, int]:
    passed = 0
    total = 2
    if _close(answer.get("answer"), _EXPECTED_DAYS):
        passed += 1
    work = answer.get("work") or dict()
    if isinstance(work, dict) and str(work.get("formula_id", "")).strip() == _FORMULA_ID:
        passed += 1
    return passed, total

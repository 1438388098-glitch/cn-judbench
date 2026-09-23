"""隐藏单测：cx-002（时效中断重新起算：2023-12-31→2024-06-16 顺延 168 天（不中断 0 / 顺延口径错均判错））。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 168
_FORMULA_ID = 'period_days'


def _close(got, want) -> bool:
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
    return abs(g - float(want)) <= 0.01


def check(answer: dict) -> tuple[int, int]:
    passed = 0
    total = 2
    if _close(answer.get("answer"), _EXPECTED):
        passed += 1
    work = answer.get("work") or dict()
    if isinstance(work, dict) and str(work.get("formula_id", "")).strip() == _FORMULA_ID:
        passed += 1
    return passed, total

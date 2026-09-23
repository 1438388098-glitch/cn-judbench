"""隐藏单测：cx-001（期间嵌套：30 日期末日 2022-01-01 遇元旦顺延至 01-04，实际占用 33 天（未顺延 30 判错））。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 33
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

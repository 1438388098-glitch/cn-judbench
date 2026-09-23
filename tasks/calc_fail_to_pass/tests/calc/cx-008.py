"""隐藏单测：cx-008（复利利息 77913.60 超约定总额封顶按 60000（无视封顶 77913.60 / 误单利 72000 判错））。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 60000.0
_FORMULA_ID = 'compound_interest_total_cap'


def _close(got, want) -> bool:
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
    return abs(g - float(want)) <= 1 or abs(g - float(want)) <= 0.005 * float(want)


def check(answer: dict) -> tuple[int, int]:
    passed = 0
    total = 2
    if _close(answer.get("answer"), _EXPECTED):
        passed += 1
    work = answer.get("work") or dict()
    if isinstance(work, dict) and str(work.get("formula_id", "")).strip() == _FORMULA_ID:
        passed += 1
    return passed, total

"""隐藏单测：cx-005（年复利两年以 15.4% 为有效利率（无视封顶 34560 / 误单利 30800 均判错））。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 33171.6
_FORMULA_ID = 'compound_annual_cap'


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

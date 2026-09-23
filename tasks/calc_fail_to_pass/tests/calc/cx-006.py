"""隐藏单测：cx-006（利息 40000 与违约金 35000 竞合择高（取低 35000 / 误复利 42000 均判错））。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 40000.0
_FORMULA_ID = 'remedy_max_interest_penalty'


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

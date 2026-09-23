"""隐藏单测：cx-007（半年复利+第2期末部分还款冲抵：实际利息 7470（不冲抵 9272.70 / 误单利 9000 判错））。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 7470.0
_FORMULA_ID = 'compound_semiannual_offset'


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

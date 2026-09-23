"""隐藏单测：cx-007（半年复利+第2期末部分还款冲抵：三年6期利息总额 11863.40（只计3期 7470 / 误单利 9000 判错））。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 11863.40
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

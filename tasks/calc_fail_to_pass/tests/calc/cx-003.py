"""隐藏单测：cx-003（封顶×部分还款冲抵本金分段计息（约定 20% 超上限须按 15.4%；未冲抵 30715.62 判错））。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 22952.33
_FORMULA_ID = 'interest_cap_offset_365'


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

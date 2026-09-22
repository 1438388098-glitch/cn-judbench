"""隐藏单测：ci-hard-001（半年复利 6 期：200000×(1.03)^6 = 238810.46；单利 236000 判错）。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 38810.46  # 生成期独立计算硬编码
_FORMULA_ID = 'compound_interest_semiannual'


def _close(got, want) -> bool:
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
    return abs(g - float(want)) <= 1 or abs(g - float(want)) <= 0.005 * float(want)
    return False


def check(answer: dict) -> tuple[int, int]:
    passed = 0
    total = 2
    if _close(answer.get("answer"), _EXPECTED):
        passed += 1
    work = answer.get("work") or dict()
    if isinstance(work, dict) and str(work.get("formula_id", "")).strip() == _FORMULA_ID:
        passed += 1
    return passed, total

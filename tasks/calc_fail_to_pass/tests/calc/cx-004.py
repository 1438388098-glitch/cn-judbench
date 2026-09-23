"""隐藏单测：cx-004（上限锁定合同成立时 LPR 15.4%（误用起诉时 13.8%→41400 判错；误用约定 18%→54000 判错））。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 46200.0
_FORMULA_ID = 'interest_cap_formation'


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

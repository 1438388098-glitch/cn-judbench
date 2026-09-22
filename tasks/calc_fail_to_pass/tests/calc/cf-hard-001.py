"""隐藏单测：cf-hard-001（保全费 = 30 + (100000-1000)×1% + (300000-100000)×0.5% = 2020；误用受理费 5800 判错）。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 2020.0  # 生成期独立计算硬编码
_FORMULA_ID = 'fee_preservation_2007'


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

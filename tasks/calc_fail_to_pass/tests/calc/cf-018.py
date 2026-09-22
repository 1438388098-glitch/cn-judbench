"""隐藏单测：cf-018（行政赔偿诉讼，标的额 10000 元）。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = 50  # 《诉讼费用交纳办法》分段累进，生成期独立计算硬编码


def _close(got, want) -> bool:
    """容差：相对误差 ≤0.5% 或绝对误差 ≤1 元。"""
    try:
        g = float(got)
    except (TypeError, ValueError):
        return False
    return abs(g - _EXPECTED) <= 1 or abs(g - _EXPECTED) <= 0.005 * _EXPECTED


def check(answer: dict) -> tuple[int, int]:
    passed = 0
    total = 2
    if _close(answer.get("answer"), _EXPECTED):
        passed += 1
    work = answer.get("work") or dict()
    if isinstance(work, dict) and str(work.get("formula_id", "")).strip() == "fee_tiered_2007":
        passed += 1
    return passed, total

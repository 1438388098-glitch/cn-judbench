"""隐藏单测：cp-hard-001（4/2 起第 30 日为 5/1（劳动节）→ 顺延至 5/6；答 5/1 或仅按周末顺延 5/2 均判错）。fail-to-pass oracle，禁读 gold。"""

_EXPECTED = '2024-05-06'  # 生成期独立计算硬编码
_FORMULA_ID = 'period_days'


def _close(got, want) -> bool:
    try:
        import re as _re
    except ImportError:
        return False
    got_s = got.strip() if isinstance(got, str) else ""
    return bool(_re.fullmatch(r"\d{4}-\d{2}-\d{2}", got_s)) and got_s == str(want)
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

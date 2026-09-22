"""案卡终态字段级 F1（impl-P3 §2.3）。"""

from __future__ import annotations

from typing import Any


def _as_set(v: Any) -> set[str]:
    if v is None:
        return set()
    if isinstance(v, (list, tuple, set)):
        return {str(x).strip() for x in v if str(x).strip()}
    return {str(v).strip()}


def state_f1(answer: Any, state_goal: dict[str, Any]) -> dict[str, Any]:
    """字段级 P/R/F1：标量精确相等；列表按元素 F1。

    返回 ``{f1, precision, recall, matched, missing, extra}``，f1 ∈ [0,1]。
    """
    if not state_goal:
        return {
            "f1": 1.0, "precision": 1.0, "recall": 1.0,
            "matched": [], "missing": [], "extra": [],
        }
    actual = answer if isinstance(answer, dict) else {}
    matched: list[str] = []
    missing: list[str] = []
    field_f1s: list[float] = []

    for key, want in state_goal.items():
        got = actual.get(key)
        want_s, got_s = _as_set(want), _as_set(got)
        if not want_s and not got_s:
            matched.append(key)
            field_f1s.append(1.0)
            continue
        if not want_s or not got_s:
            missing.append(key)
            field_f1s.append(0.0)
            continue
        inter = want_s & got_s
        prec = len(inter) / len(got_s)
        rec = len(inter) / len(want_s)
        f1 = 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
        field_f1s.append(f1)
        if f1 >= 1.0:
            matched.append(key)
        else:
            missing.append(key)

    extra = [k for k in actual if k not in state_goal and k not in (
        "citations", "law_anchors", "notes", "steps", "meta",
    )]
    f1 = sum(field_f1s) / len(field_f1s) if field_f1s else 0.0
    prec = (len(matched) / max(1, len(matched) + len(extra))) if state_goal else 1.0
    rec = len(matched) / max(1, len(state_goal))
    # 综合：字段平均 F1 与宏 P/R 调和后取主口径 = 字段平均 F1（稳定、可 fmt2）
    return {
        "f1": f1,
        "precision": prec,
        "recall": rec,
        "matched": matched,
        "missing": missing,
        "extra": extra,
    }

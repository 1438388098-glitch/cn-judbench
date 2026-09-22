"""案卡终态字段级 F1（impl-P3 §2.3，含键别名与标签归一）。"""

from __future__ import annotations

from typing import Any

from ..score.norm import KEY_ALIASES, find_key, set_f1


def _as_list(v: Any) -> list:
    if v is None:
        return []
    if isinstance(v, (list, tuple, set)):
        return [x for x in v if x is not None and str(x).strip() != ""]
    return [v] if str(v).strip() != "" else []


def state_f1(answer: Any, state_goal: dict[str, Any]) -> dict[str, Any]:
    """字段级 P/R/F1：标量经归一化/包含匹配；列表按元素 F1。

    返回 ``{f1, precision, recall, matched, missing, extra}``，f1 ∈ [0,1]。
    金样未要求的字段（want 空）不因模型多写而记 0——无可比目标即 1.0。
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
        got = find_key(actual, key)
        w_list, g_list = _as_list(want), _as_list(got)
        f1, tp, n_want = set_f1(g_list, w_list)
        if n_want == 0:
            # 金样无该字段目标：跳过（不进均值），避免空 want + 有 got 记 0
            matched.append(key)
            continue
        field_f1s.append(f1)
        if f1 >= 0.999:
            matched.append(key)
        else:
            missing.append(key)

    known_keys = set(state_goal) | {
        a for k in state_goal for a in KEY_ALIASES.get(k, ())
    }
    extra = [
        k for k in actual
        if k not in known_keys and k not in (
            "citations", "law_anchors", "notes", "steps", "meta",
            "case_card", "state_goal", "expect", "progress", "calls", "negative",
        )
    ]
    f1 = sum(field_f1s) / len(field_f1s) if field_f1s else 1.0
    prec = (len(matched) / max(1, len(matched) + len(extra))) if state_goal else 1.0
    rec = len(matched) / max(1, len(state_goal))
    return {
        "f1": f1,
        "precision": prec,
        "recall": rec,
        "matched": matched,
        "missing": missing,
        "extra": extra,
    }

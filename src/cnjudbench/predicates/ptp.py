"""PTP（不得破坏）谓词实现（impl-P0b §3.2）。

仅限可机检范围（§4.2.1 收窄表）；自由文本语义 PTP **不做**。
"""

from __future__ import annotations

from .base import EvalContext, PredicateResult
from .ftp import _as_iso_date, _walk
from ..lawkb.resolve import normalize_law_name


def must_not_statute(ctx: EvalContext, p, index: int) -> PredicateResult:
    """禁引：输出引用 ∩ 禁引表 = ∅（law_id 命中或归一化名命中均算）。"""
    extra = p.model_extra or {}
    forbidden = extra.get("laws") or ([extra["law"]] if extra.get("law") else [])
    forbidden_ids: set[str] = set()
    forbidden_names: set[str] = set()
    for name in forbidden:
        forbidden_names.add(normalize_law_name(str(name)))
        if (lid := ctx.store.alias.get(normalize_law_name(str(name)))):
            forbidden_ids.add(lid)

    violations: list[str] = []
    for c, chk in zip(ctx.claims, ctx.checks):
        claim_norm = normalize_law_name(c.law_raw)
        claim_law_id = ctx.store.alias.get(claim_norm)
        if (claim_law_id and claim_law_id in forbidden_ids) or (claim_norm in forbidden_names):
            violations.append(c.law_raw)

    ok = not violations
    return PredicateResult("ptp", index, "must_not_statute", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail="; ".join(f"禁引 {v}" for v in violations) or "无禁引",
                           failure_taxonomy=None if ok else "wrong_article")


def field_keep(ctx: EvalContext, p, index: int) -> PredicateResult:
    """已知事实保持：answer[path] 不得被改坏。

    期望值来源优先级：``expect``（字面）> ``expect_from: item.as_of`` >
    ``gold[expect_path|path]``。
    """
    extra = p.model_extra or {}
    path = extra.get("path", "")
    got = _walk(path, ctx.answer) if ctx.answer else None
    if extra.get("expect") is not None:
        want = extra["expect"]
    elif extra.get("expect_from") == "item.as_of":
        want = ctx.item.as_of.isoformat()
    else:
        want = _walk(extra.get("expect_path") or path, ctx.item.gold)

    got_s = _as_iso_date(got) or (str(got).strip() if got is not None else None)
    want_s = _as_iso_date(want) or (str(want).strip() if want is not None else None)
    ok = got_s is not None and got_s == want_s
    return PredicateResult("ptp", index, "field_keep", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail=f"{path}: {got!r} vs {want!r}",
                           failure_taxonomy=None if ok else "state_drift")


def state(ctx: EvalContext, p, index: int) -> PredicateResult:
    """终态子集匹配：expect 键值须悉数出现在 answer（键别名 + 归一化）。

    期望值来源：谓词 ``expect`` > ``item.state_goal``（τ-Jud 金样，去掉元键）。
    """
    from ..score.norm import find_key, labels_match

    extra = p.model_extra or {}
    expect: dict = extra.get("expect") or {}
    if not expect and isinstance(ctx.item.state_goal, dict):
        expect = {
            k: v for k, v in ctx.item.state_goal.items()
            if k not in ("expect", "progress", "calls", "negative", "citations", "law_anchors")
        }
    actual = _walk(extra.get("path", ""), ctx.answer) if ctx.answer else None
    actual = actual if isinstance(actual, dict) else (ctx.answer if isinstance(ctx.answer, dict) else {})
    missing = {}
    for k, v in expect.items():
        got = find_key(actual, k) if isinstance(actual, dict) else None
        if isinstance(v, list):
            from ..score.norm import set_f1
            f1, _, n = set_f1(got, v)
            if n and f1 < 0.999:
                missing[k] = v
        elif got is None or not (got == v or labels_match(got, v)):
            # severity 枚举
            from ..score.norm import normalize_severity
            if not (got is not None and normalize_severity(got) == normalize_severity(v)
                    and normalize_severity(v) in ("high", "medium", "low")):
                missing[k] = v
    ok = not missing
    return PredicateResult("ptp", index, "state", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail=f"终态不符: {missing}" if missing else "终态一致",
                           failure_taxonomy=None if ok else "state_drift")

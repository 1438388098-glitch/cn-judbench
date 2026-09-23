"""PTP（不得破坏）谓词实现（impl-P0b §3.2）。

仅限可机检范围（§4.2.1 收窄表）；自由文本语义 PTP **不做**。
"""

from __future__ import annotations

from .base import EvalContext, PredicateResult
from .ftp import _as_iso_date, _walk
from ..lawkb.resolve import alias_lookup, normalize_law_name


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
        claim_law_id = alias_lookup(ctx.store, c.law_raw)
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
    """终态匹配：expect 键值逐键打分，pass_ratio = 键均分（v0.6 部分得分改造）。

    期望值来源：谓词 ``expect`` > ``item.state_goal``（τ-Jud 金样，去掉元键）。
    - 标量键：精确/归一化/severity 同义命中 = 1.0；未命中退化为 set_f1 重叠
      （自由文本字段的同义改写可获部分分，不再全有全无）；
    - 列表键：set_f1 元素级得分。
    ok 语义不变（全部键 ≥0.999）；ratio 供 on_fail=partial 比例计分。
    """
    from ..score.norm import find_key, labels_match, polarity_opposed, set_f1, text_coverage

    extra = p.model_extra or {}
    expect: dict = extra.get("expect") or {}
    if not expect and isinstance(getattr(ctx.item, "state_goal", None), dict):
        expect = {
            k: v for k, v in ctx.item.state_goal.items()
            if k not in ("expect", "progress", "calls", "negative", "citations", "law_anchors")
        }
    actual = _walk(extra.get("path", ""), ctx.answer) if ctx.answer else None
    actual = actual if isinstance(actual, dict) else (ctx.answer if isinstance(ctx.answer, dict) else {})
    from ..score.norm import normalize_severity

    per_key: dict[str, float] = {}
    for k, v in expect.items():
        got = find_key(actual, k) if isinstance(actual, dict) else None
        if isinstance(v, list):
            f1, _, n = set_f1(got, v)
            per_key[k] = f1 if n else 1.0  # 金样无该键目标 → 不扣（与 state_f1 一致）
        elif got is None:
            per_key[k] = 0.0
        elif got == v or labels_match(got, v):
            per_key[k] = 1.0
        elif (normalize_severity(got) == normalize_severity(v)
              and normalize_severity(v) in ("high", "medium", "low")):
            per_key[k] = 1.0
        else:
            # 未达二元命中阈值：极性反转计 0（不支持≠支持，c323）；
            # 同义改写按 bigram 覆盖率给连续部分分（不再归零）
            per_key[k] = (0.0 if polarity_opposed(got, v)
                          else min(1.0, text_coverage(got, v)))
    ratio = sum(per_key.values()) / len(per_key) if per_key else 1.0
    ok = all(s >= 0.999 for s in per_key.values()) if per_key else True
    missed = {k: round(s, 2) for k, s in per_key.items() if s < 0.999}
    return PredicateResult("ptp", index, "state", ok, min(1.0, ratio), p.on_fail,
                           detail=f"终态键分: {per_key}" if per_key else "终态一致（无期望键）",
                           failure_taxonomy=None if ok else "state_drift")

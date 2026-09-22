"""FTP（应命中）谓词实现（impl-P0b §3.2）。

约定：
- ``pass_ratio`` 直接进入题分基数（各 FTP 均值 ×100）；
- ``on_fail: partial`` 的额外惩罚为空——比例已体现在基数里；
- statute / no_fabrication 全部经 CiteGuard 解析后判定，**不做原文正则**。
"""

from __future__ import annotations

from datetime import date

from ..lawkb.resolve import normalize_article_no, normalize_law_name
from .base import EvalContext, PredicateResult


def _walk(path: str, obj) -> object:
    cur: object = obj
    for part in path.split("."):
        if isinstance(cur, list) and part.lstrip("-").isdigit():
            i = int(part)
            if -len(cur) <= i < len(cur):
                cur = cur[i]
            else:
                return None
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _as_float(v) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("¥", "").replace("元", "")
    try:
        return float(s)
    except ValueError:
        return None


def _as_iso_date(v) -> str | None:
    s = str(v).strip()
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        return None


def statute(ctx: EvalContext, p, index: int) -> PredicateResult:
    """必引核验：输出引用须覆盖题面 law_anchors，且经三检 ok。

    taxonomy 细分（§4.2 三检表）：完全没引到 → ``miss_retrieve``；
    条号命中但时效不过 → ``stale_statute``；其余（条号/法名错）→ ``wrong_article``。
    """
    on_fail = p.on_fail
    required = ctx.item.law_anchors
    if ctx.claim_status == "claim_extract_miss" and ctx.task.output_type == "gen":
        # 仅 gen 允许降级（§4.2 脚注：抽不到 claim 降级 rubric gate）；
        # structured/extract 缺 citations 视为未引，按 miss_retrieve 判
        return PredicateResult("ftp", index, "statute", True, 1.0, on_fail,
                               detail="claim_extract_miss：降级 P1 rubric gate，不机判")

    covered = 0
    stale_hit = False
    for anchor in required:
        anchor_law_id = ctx.store.alias.get(normalize_law_name(anchor.law))
        anchor_ano = normalize_article_no(anchor.article)
        for c, chk in zip(ctx.claims, ctx.checks):
            claim_law_id = ctx.store.alias.get(normalize_law_name(c.law_raw))
            if claim_law_id != anchor_law_id or normalize_article_no(c.article_raw) != anchor_ano:
                continue
            if chk.ok:
                covered += 1
                break
            if chk.taxonomy == "stale_statute":
                stale_hit = True

    ratio = covered / len(required) if required else 1.0
    taxonomy = None
    if ratio < 1.0:
        if stale_hit:
            taxonomy = "stale_statute"
        else:
            taxonomy = "miss_retrieve" if not ctx.claims else "wrong_article"
    return PredicateResult("ftp", index, "statute", ratio >= 1.0, ratio, on_fail,
                           detail=f"必引覆盖 {covered}/{len(required)}",
                           failure_taxonomy=taxonomy)


def element(ctx: EvalContext, p, index: int) -> PredicateResult:
    """要件命中：answer[path] 与 gold[gold_path] 的集合 F1。"""
    extra = p.model_extra or {}
    got = _walk(extra.get("path", ""), ctx.answer) if ctx.answer else None
    want = _walk(extra.get("gold_path") or extra.get("path", ""), ctx.item.gold) if isinstance(ctx.item.gold, dict) else None
    got_set = set(map(str, got)) if isinstance(got, (list, tuple)) else ({str(got)} if got is not None else set())
    want_set = set(map(str, want)) if isinstance(want, (list, tuple)) else ({str(want)} if want is not None else set())
    if not want_set:
        return PredicateResult("ftp", index, "element", False, 0.0, p.on_fail,
                               detail="gold 无可比要件", failure_taxonomy="element_miss")
    tp = len(got_set & want_set)
    precision = tp / len(got_set) if got_set else 0.0
    recall = tp / len(want_set)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return PredicateResult("ftp", index, "element", f1 >= 1.0, f1, p.on_fail,
                           detail=f"F1={f1:.4f}（命中 {tp}/{len(want_set)}）",
                           failure_taxonomy=None if f1 >= 1.0 else "element_miss")


def field(ctx: EvalContext, p, index: int) -> PredicateResult:
    """字段命中：answer[path] == gold[gold_path|path]（可配别名表、可配失败 taxonomy）。

    ``gold_path`` 相对 item.gold 根；列表索引用数字段（如 ``0.expect_status``）。
    """
    extra = p.model_extra or {}
    path = extra.get("path", "")
    got = _walk(path, ctx.answer) if ctx.answer else None
    want = _walk(extra.get("gold_path") or path, ctx.item.gold) if isinstance(ctx.item.gold, dict) or isinstance(ctx.item.gold, list) else None
    accepted = {str(v).strip() for v in extra.get("aliases", {}).get(str(want), [want])}
    ok = got is not None and str(got).strip() in accepted
    taxonomy = None if ok else extra.get("fail_taxonomy", "element_miss")
    return PredicateResult("ftp", index, "field", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail=f"{path}: {got!r} vs {want!r}",
                           failure_taxonomy=taxonomy)


def amount(ctx: EvalContext, p, index: int) -> PredicateResult:
    """金额/数值：精确或容差（默认 0）。"""
    extra = p.model_extra or {}
    path = extra.get("path", "")
    got = _as_float(_walk(path, ctx.answer)) if ctx.answer else None
    want = _as_float(_walk(extra.get("gold_path") or path, ctx.item.gold))
    tol = float(extra.get("tolerance", 0))
    ok = got is not None and want is not None and abs(got - want) <= tol
    return PredicateResult("ftp", index, "amount", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail=f"{path}: {got!r} vs {want!r} (tol={tol})",
                           failure_taxonomy=None if ok else "element_miss")


def deadline(ctx: EvalContext, p, index: int) -> PredicateResult:
    """期间/日期：ISO 相等。"""
    extra = p.model_extra or {}
    path = extra.get("path", "")
    got = _as_iso_date(_walk(path, ctx.answer)) if ctx.answer else None
    want = _as_iso_date(_walk(extra.get("gold_path") or path, ctx.item.gold))
    ok = got is not None and got == want
    return PredicateResult("ftp", index, "deadline", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail=f"{path}: {got!r} vs {want!r}",
                           failure_taxonomy=None if ok else "element_miss")


def no_fabrication(ctx: EvalContext, p, index: int) -> PredicateResult:
    """不得编造：声称的 version_id 须与 lawkb 解析一致。

    未入库/法名未命中（unknown_in_lawkb / unresolved_law）**不算**违规——
    框架原则「unknown 分列不记幻觉」（impl §4.2），仅在 detail 分列；
    声称的 version_id 与库矛盾才记 ``fabricated_case``。
    """
    if ctx.claim_status == "claim_extract_miss" and ctx.task.output_type == "gen":
        return PredicateResult("ftp", index, "no_fabrication", True, 1.0, p.on_fail,
                               detail="claim_extract_miss：降级 P1 rubric gate，不机判")
    violations: list[str] = []
    notes: list[str] = []
    taxonomy = None
    for c, chk in zip(ctx.claims, ctx.checks):
        if chk.ambiguous:
            notes.append(f"{c.law_raw}:{c.article_raw} ambiguous（库数据错误）")
        elif c.version_id and chk.exists and c.version_id != chk.version_id:
            violations.append(f"version_id 编造: {c.version_id} ≠ {chk.version_id}")
            taxonomy = "fabricated_case"
        elif not chk.exists:
            notes.append(f"{c.law_raw}:{c.article_raw} {chk.resolve_status}（分列，不记幻觉）")
    ok = not violations
    return PredicateResult("ftp", index, "no_fabrication", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail="; ".join(violations) or ("；".join(notes) or "声称的 version_id 均与库一致"),
                           failure_taxonomy=taxonomy)


def schema_lint(ctx: EvalContext, p, index: int) -> PredicateResult:
    """栏目级 schema：answer 含必需键（on_fail 默认 flag，不改分）。"""
    required = (p.model_extra or {}).get("required", [])
    keys = set(ctx.answer) if isinstance(ctx.answer, dict) else set()
    missing = [k for k in required if k not in keys]
    ok = not missing
    return PredicateResult("ftp", index, "schema", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail=f"缺栏: {missing}" if missing else "栏目齐备",
                           failure_taxonomy=None if ok else "format_fail")

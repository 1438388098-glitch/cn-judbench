"""FTP（应命中）谓词实现（impl-P0b §3.2）。

约定：
- ``pass_ratio`` 直接进入题分基数（各 FTP 均值 ×100）；
- ``on_fail: partial`` 的额外惩罚为空——比例已体现在基数里；
- statute / no_fabrication 全部经 CiteGuard 解析后判定，**不做原文正则**。
"""

from __future__ import annotations

import re
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
        # skipped=True 不进 FTP 基数，禁止用 1.0 充数（评分总则「缺评 n/a」）
        return PredicateResult("ftp", index, "statute", True, 1.0, on_fail,
                               detail="claim_extract_miss：降级 P1 rubric gate，不机判",
                               skipped=True)

    covered = 0
    stale_hit = False
    same_law_other = 0
    for anchor in required:
        anchor_law_id = ctx.store.alias.get(normalize_law_name(anchor.law))
        anchor_ano = normalize_article_no(anchor.article)
        hit_exact = False
        hit_same_law = False
        for c, chk in zip(ctx.claims, ctx.checks):
            claim_law_id = ctx.store.alias.get(normalize_law_name(c.law_raw))
            # 双方均须解析成功；双失败时 None==None 不得误判同法（P0-1）
            if anchor_law_id is None or claim_law_id is None or claim_law_id != anchor_law_id:
                continue
            if normalize_article_no(c.article_raw) != anchor_ano:
                if chk.ok:
                    hit_same_law = True
                continue
            if chk.ok:
                hit_exact = True
                break
            if chk.taxonomy == "stale_statute":
                stale_hit = True
        if hit_exact:
            covered += 1
        elif hit_same_law:
            # 真实模型常引同法更贴案情的条文（如借款 667 vs 金样 577）——给 0.5 而非 0
            same_law_other += 1

    n = len(required) if required else 1
    raw_ratio = (covered + 0.5 * same_law_other) / n if required else 1.0
    taxonomy = None
    # 同法异条且非 stale → 记 PASS 但 ratio<1（进基数 partial，**不触发** on_fail=zero）
    # stale / 完全未引 → FAIL，交给任务包 on_fail（wrong_vintage 金样仍须 0.00）
    if covered >= len(required):
        passed, ratio = True, 1.0
    elif same_law_other > 0 and not stale_hit:
        passed, ratio = True, min(1.0, raw_ratio)
        taxonomy = "wrong_article"
    else:
        passed, ratio = False, min(1.0, raw_ratio)
        if stale_hit:
            taxonomy = "stale_statute"
        else:
            taxonomy = "miss_retrieve" if not ctx.claims else "wrong_article"
    # 同法异条 PASS 也保留 taxonomy（wrong_article），供报表机读（P1-4）
    return PredicateResult("ftp", index, "statute", passed, ratio, on_fail,
                           detail=f"必引覆盖 {covered}/{len(required)}"
                                  + (f" +同法异条 {same_law_other}" if same_law_other else ""),
                           failure_taxonomy=taxonomy)


def element(ctx: EvalContext, p, index: int) -> PredicateResult:
    """要件命中：answer[path] 与 gold[gold_path] 的集合 F1（含归一化/包含匹配）。"""
    from ..score.norm import find_key, set_f1

    extra = p.model_extra or {}
    path = extra.get("path", "")
    got = _walk(path, ctx.answer) if ctx.answer else None
    if got is None and isinstance(ctx.answer, dict) and path:
        got = find_key(ctx.answer, path.rsplit(".", 1)[-1])
    want = _walk(extra.get("gold_path") or path, ctx.item.gold) if isinstance(ctx.item.gold, dict) else None
    if want is None and isinstance(ctx.item.gold, dict) and path:
        want = find_key(ctx.item.gold, path.rsplit(".", 1)[-1])
    f1, tp, n_want = set_f1(got, want)
    if not n_want:
        # 金样配置不可比 → 拒判级跳过，禁止用 0.00 充数（评分总则）
        return PredicateResult("ftp", index, "element", True, 1.0, p.on_fail,
                               detail="gold 无可比要件：跳过机判（n/a）",
                               skipped=True)
    return PredicateResult("ftp", index, "element", f1 >= 1.0, f1, p.on_fail,
                           detail=f"F1={f1:.4f}（命中 {tp}/{n_want}）",
                           failure_taxonomy=None if f1 >= 1.0 else "element_miss")


def field(ctx: EvalContext, p, index: int) -> PredicateResult:
    """字段命中：answer[path] 对 gold（支持 exact / contains / severity）。

    真实模型会写「中高」「…合同欠款纠纷」等同义/更长表述——默认对
    severity 枚举自动归一，其余用 ``match: exact|contains``（默认 exact，
    松匹配必须显式声明，防放水）。
    """
    from ..score.norm import article_set, find_key, labels_match, normalize_severity

    extra = p.model_extra or {}
    path = extra.get("path", "")
    got = _walk(path, ctx.answer) if ctx.answer else None
    if got is None and isinstance(ctx.answer, dict) and path:
        got = find_key(ctx.answer, path.rsplit(".", 1)[-1])
    want = _walk(extra.get("gold_path") or path, ctx.item.gold) if isinstance(ctx.item.gold, dict) or isinstance(ctx.item.gold, list) else None
    if want is None and isinstance(ctx.item.gold, dict) and path:
        want = find_key(ctx.item.gold, path.rsplit(".", 1)[-1])

    mode = str(extra.get("match") or "exact")
    ok = False
    ratio = 1.0
    detail = f"{path}: {got!r} vs {want!r}"
    if mode == "article_set":
        gs, ws = article_set(got), article_set(want)
        ok = bool(ws) and ws <= gs
        ratio = (len(gs & ws) / len(ws)) if ws else 0.0
        detail = f"{path}: arts {sorted(gs)} ⊇ {sorted(ws)} (cov={ratio:.2f})"
    elif mode == "severity":
        ok = got is not None and normalize_severity(got) == normalize_severity(want) and normalize_severity(want) != ""
        detail = f"{path}: sev {got!r}~{want!r} → {normalize_severity(got)!r}"
    elif mode == "contains":
        from ..score.norm import text_coverage
        ratio = text_coverage(got, want) if got is not None else 0.0
        ok = ratio >= 0.55
        detail = f"{path}: cov={ratio:.2f} {got!r} ~ {want!r}"
    elif mode == "labels":
        # 显式松匹配（含同义/包含）；默认 exact 不走此支
        ok = got is not None and labels_match(got, want)
        ratio = 1.0 if ok else 0.0
        detail = f"{path}: labels {got!r} ~ {want!r}"
    else:
        # exact：只比 accepted/别名，**禁止** labels_match 自动放水（P1-1）
        aliases = extra.get("aliases") or {}
        if not isinstance(aliases, dict):
            aliases = {}
        accepted = {str(v).strip() for v in aliases.get(str(want), [want]) if v is not None}
        accepted |= {str(want).strip()} if want is not None else set()
        ok = got is not None and str(got).strip() in accepted
        ratio = 1.0 if ok else 0.0
    taxonomy = None if ok else extra.get("fail_taxonomy", "element_miss")
    # partial 时把覆盖率写入 pass_ratio（与 element 一致进基数）
    pass_ratio = 1.0 if ok else (ratio if p.on_fail == "partial" else 0.0)
    return PredicateResult("ftp", index, "field", ok, pass_ratio, p.on_fail,
                           detail=detail, failure_taxonomy=taxonomy)


def amount(ctx: EvalContext, p, index: int) -> PredicateResult:
    """金额/数值：精确或容差（默认 0）。"""
    extra = p.model_extra or {}
    path = extra.get("path", "")
    got_raw = _walk(path, ctx.answer) if ctx.answer else None
    want_raw = _walk(extra.get("gold_path") or path, ctx.item.gold)
    # bool 不是数值（True 会被当成 1）
    if isinstance(got_raw, bool) or isinstance(want_raw, bool):
        return PredicateResult("ftp", index, "amount", False, 0.0, p.on_fail,
                               detail=f"{path}: bool 不得作金额", failure_taxonomy="element_miss")
    got = _as_float(got_raw)
    want = _as_float(want_raw)
    try:
        tol = float(extra.get("tolerance", 0) or 0)
    except (TypeError, ValueError):
        tol = 0.0
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
                               detail="claim_extract_miss：降级 P1 rubric gate，不机判",
                               skipped=True)
    violations: list[str] = []
    notes: list[str] = []
    taxonomy = None
    for c, chk in zip(ctx.claims, ctx.checks):
        if chk.ambiguous:
            notes.append(f"{c.law_raw}:{c.article_raw} ambiguous（库数据错误）")
        elif c.version_id and chk.exists and c.version_id != chk.version_id:
            vid = str(c.version_id).strip()
            # 仅当声称值形如库内 version_id（如 cl_264_2011）才判「编造」；
            # 「刑法（2023修正）」等叙述性标签不是库主键，不记 fabricated_case
            if re.fullmatch(r"[a-z][a-z0-9_]{2,}", vid):
                violations.append(f"version_id 编造: {vid} ≠ {chk.version_id}")
                taxonomy = "fabricated_case"
            else:
                notes.append(f"version_id 为叙述性标签，不判编造: {vid[:40]}")
        elif not chk.exists:
            notes.append(f"{c.law_raw}:{c.article_raw} {chk.resolve_status}（分列，不记幻觉）")
    ok = not violations
    return PredicateResult("ftp", index, "no_fabrication", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail="; ".join(violations) or ("；".join(notes) or "声称的 version_id 均与库一致"),
                           failure_taxonomy=taxonomy)


def schema_lint(ctx: EvalContext, p, index: int) -> PredicateResult:
    """栏目级 schema：answer 含必需键（支持键别名；on_fail 默认 flag，不改分）。"""
    from ..score.norm import find_key

    required = (p.model_extra or {}).get("required", [])
    keys = set(ctx.answer) if isinstance(ctx.answer, dict) else set()
    missing = [k for k in required if find_key(ctx.answer, k) is None]
    ok = not missing
    return PredicateResult("ftp", index, "schema", ok, 1.0 if ok else 0.0, p.on_fail,
                           detail=f"缺栏: {missing}" if missing else "栏目齐备",
                           failure_taxonomy=None if ok else "format_fail")


_RISK_MARKS = (
    "风险", "时效", "败诉", "不能保证", "无法保证", "仅供参考", "建议咨询",
    "不利后果", "举证", "执行不能", "不确定性",
)
_REFUSE_MARKS = (
    "无法回答", "不能提供", "拒绝回答", "建议咨询律师", "请咨询执业律师",
    "不予代理", "不能代理", "转介",
)


def risk_disclosure(ctx: EvalContext, p, index: int) -> PredicateResult:
    """风险披露（Proto #2）：答案文本须含风险/不确定提示，不得作结果保证。

    机检口径：关键词命中 + 与 Abst over_promise 互斥；细节语义进 Judge 列。
    """
    extra = p.model_extra or {}
    marks = tuple(extra.get("match") or _RISK_MARKS)
    text = ctx.answer_text or ""
    if isinstance(ctx.answer, dict):
        for key in ("advice", "risk_note", "risks", "disclosure"):
            if key in ctx.answer:
                text += "\n" + str(ctx.answer[key])
    found = [m for m in marks if m in text]
    from ..judge.abst import label_abst

    promised = label_abst(ctx.answer_text or "", expect="answer").over_promise
    ok = bool(found) and not promised
    return PredicateResult(
        "ftp", index, "risk_disclosure", ok, 1.0 if ok else 0.0, p.on_fail,
        detail=f"风险提示 {found}" if ok else f"缺风险披露或含结果承诺（found={found}）",
        failure_taxonomy=None if ok else "over_promise" if promised else "element_miss",
    )


def refuse(ctx: EvalContext, p, index: int) -> PredicateResult:
    """应拒/应答（Proto #4）：``expect: refuse|answer``。

    应拒却答且作承诺 → over_promise；应答却空拒 → over_refuse。
    """
    extra = p.model_extra or {}
    expect = str(extra.get("expect") or "answer")
    text = (ctx.answer_text or "").strip()
    from ..judge.abst import label_abst

    lab = label_abst(text, expect=expect)
    if expect == "refuse":
        refused = any(m in text for m in _REFUSE_MARKS)
        ok = refused and not lab.over_promise
        detail = "已拒绝并转介" if ok else "应拒未拒或作结果承诺"
        tax = None if ok else "over_promise"
    else:
        ok = not lab.over_refuse and not lab.over_promise
        detail = "正常作答" if ok else (
            "over_refuse" if lab.over_refuse else "over_promise"
        )
        tax = None if ok else ("over_refuse" if lab.over_refuse else "over_promise")
    return PredicateResult(
        "ftp", index, "refuse", ok, 1.0 if ok else 0.0, p.on_fail,
        detail=detail, failure_taxonomy=tax,
    )


def progress_keyword(ctx: EvalContext, p, index: int) -> PredicateResult:
    """多步 progress（弱指标，on_fail 默认 flag 不改分；诊断列单独展示）。

    关键词来源：谓词 ``match`` 键，缺省回落 ``item.gold.progress``。
    """
    extra = p.model_extra or {}
    kws = list(extra.get("match") or [])
    if not kws and isinstance(ctx.item.gold, dict):
        kws = list(ctx.item.gold.get("progress") or [])
    if not kws:
        return PredicateResult("ftp", index, "progress_keyword", True, 1.0, p.on_fail,
                               detail="无 progress 关键词，跳过")
    text = ctx.answer_text or ""
    found = [k for k in kws if k in text]
    missing = [k for k in kws if k not in text]
    ratio = len(found) / len(kws)
    return PredicateResult("ftp", index, "progress_keyword", ratio >= 1.0, ratio, p.on_fail,
                           detail=f"progress {len(found)}/{len(kws)}"
                                  + (f"，缺 {missing}" if missing else ""))

"""谓词注册表与题分合成（impl-P0b §3.1/§3.3）。

- 执行前先过 §4.2.1 适用面矩阵；不适用 → **拒判报错**（PredicateError），不静默跳过；
- 题分合成顺序（强制）：FTP 基数 → PTP 调整 → on_fail=zero 一票否决 → fmt2。
"""

from __future__ import annotations

from ..schemas.task import PredicatesFile
from ..validate.matrix import predicate_allowed, ptp_allowed
from . import ftp, ptp
from .base import EvalContext, PredicateError, PredicateResult
from .tools import fake_tool, tool_ast, tool_sequence

FTP_IMPLS = {
    "statute": ftp.statute,
    "element": ftp.element,
    "field": ftp.field,
    "amount": ftp.amount,
    "deadline": ftp.deadline,
    "no_fabrication": ftp.no_fabrication,
    "schema": ftp.schema_lint,
    "lint": ftp.schema_lint,
    "progress_keyword": ftp.progress_keyword,
    "risk_disclosure": ftp.risk_disclosure,
    "refuse": ftp.refuse,
    "status_ladder": ftp.status_ladder,
    "unit_tests": ftp.unit_tests,
    "fake_tool": fake_tool,
}

PTP_IMPLS = {
    "must_not_statute": ptp.must_not_statute,
    "field_keep": ptp.field_keep,
    "state": ptp.state,
    "tool_sequence": tool_sequence,
    "tool_ast": tool_ast,
}


def _run_set(
    ctx: EvalContext,
    set_name: str,
    predicates,
    impls: dict,
    allowed_fn,
) -> list[PredicateResult]:
    results: list[PredicateResult] = []
    for i, p in enumerate(predicates):
        if p.type not in impls:
            raise PredicateError(f"谓词 {p.type!r} 在 P0b 执行器中未实现（拒判，不静默跳过）")
        if not allowed_fn(p.type, ctx.task.output_type, ctx.task.components):
            raise PredicateError(
                f"谓词 {p.type!r} 不适用于 output_type={ctx.task.output_type!r}（§4.2.1）"
            )
        results.append(impls[p.type](ctx, p, i))
        results[-1].set_name = set_name
    return results


def evaluate_predicates(
    ctx: EvalContext, preds: PredicatesFile
) -> tuple[list[PredicateResult], list[PredicateResult], list[PredicateResult]]:
    """返回 (ftp, ptp, diagnostic_ftp) 三组结果。"""
    ftp_results = _run_set(ctx, "ftp", preds.ftp, FTP_IMPLS, predicate_allowed)
    ptp_results = _run_set(ctx, "ptp", preds.ptp, PTP_IMPLS, ptp_allowed)
    diag = _run_set(ctx, "diagnostic_ftp", preds.diagnostic_ftp, FTP_IMPLS, predicate_allowed)
    return ftp_results, ptp_results, diag


def compose_score(
    ftp_results: list[PredicateResult], ptp_results: list[PredicateResult]
) -> tuple[float, list[str]]:
    """题分合成（DESIGN v0.4 §4.1 ②：oracle_raw → 红线处置，写死）。

    - **基数 = on_fail=partial 且非 skipped 的 FTP 比例均值 ×100**：partial 谓词计分
      （oracle_raw）；zero/cap_50 谓词只作红线门禁，其比例不进基数（避免门禁通过
      把阶梯 0 分稀释抬升，如 cit no_fabrication 1.0 × status_ladder 0 → 50）；
    - on_fail=zero 失败 / stale_statute → 本题 0.00（优先于一切 cap）；
    - cap_50 失败 → 封顶 50.00；
    - Hall：fabricated_case 每处 −20.00，下限 0.00；
    - taxonomy：失败与「PASS 但带 taxonomy」（如 wrong_article）均收集。
    """
    taxonomy: list[str] = []

    # 基数 = partial 且非 skipped 的 FTP 比例均值 ×100；无 partial 谓词（纯门禁题）→ 100
    scored = [r for r in ftp_results if r.on_fail == "partial" and not r.skipped]
    base = 100.0 * sum(r.pass_ratio for r in scored) / len(scored) if scored else 100.0
    final = base

    zero_trigger = False
    stale_trigger = False
    hall_hits = 0
    for r in list(ftp_results) + list(ptp_results):
        if r.skipped:
            continue
        if r.failure_taxonomy:
            taxonomy.append(r.failure_taxonomy)
            if r.failure_taxonomy == "stale_statute":
                stale_trigger = True
            if r.failure_taxonomy == "fabricated_case":
                hall_hits += 1
        if r.passed:
            continue
        if r.on_fail == "zero":
            zero_trigger = True
        elif r.on_fail == "cap_50":
            final = min(final, 50.0)
        elif r.on_fail == "partial" and r in ptp_results:
            final *= r.pass_ratio
        # FTP partial：比例已在基数中；flag：不改分

    # Hall 题级扣分（§8.1 ②）：每处重大幻觉 −20.00，下限 0.00
    if hall_hits and not zero_trigger:
        final = max(0.0, final - 20.0 * hall_hits)

    # stale/wrong_vintage 与假调用等 zero 一票否决（zero 优先于 cap）
    if zero_trigger or stale_trigger:
        final = 0.0
    return final, taxonomy

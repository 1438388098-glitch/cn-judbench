"""工具调用谓词（impl-P2 §3/§5）。

判分语义（impl-P2 §6）：题分 = 答案分 × 工具序列匹配 × 参数正确 − fake_tool 零分。
- ``fake_tool``（FTP，zero）：声称的调用在沙箱无日志 / 调了未注册工具 → 一票否决；
- ``tool_sequence``（PTP，partial）：期望工具子集匹配，pass_ratio = 覆盖比例；
- ``tool_ast``（PTP，partial）：调用参数过沙箱 schema，pass_ratio = 合法比例。

PTP partial 乘法链与 §6 公式一致：compose_score 对 PTP partial 逐项 `final *= ratio`。
"""

from __future__ import annotations

import re

from .base import EvalContext, PredicateResult

# 只叙述不调用的话术（假调用启发式；仅在**无任何调用日志**时参与判定）
_NARRATIVE_RE = re.compile(r"(我|已|经)(已)?(搜索|查询|检索|查阅|调取|计算了)")


def fake_tool(ctx: EvalContext, p, index: int) -> PredicateResult:
    """假调用检测（FTP）：期望工具但无成功日志 / 未注册工具名 / 只叙述不调用。"""
    expected: list[str] = []
    if isinstance(ctx.item.gold, dict):
        expected = list(ctx.item.gold.get("expected_tools") or [])
    log = ctx.tool_log
    unknown = [e.name for e in log if e.error == "unknown_tool"]
    called_names = {e.name for e in log}
    executed = [e for e in log if e.ok]

    violations: list[str] = []
    if unknown:
        violations.append(f"未注册工具: {unknown}")
    # 期望工具须真的出现在调用日志（含业务失败），不能被无关成功调用顶替（P1-9）
    if expected and not (set(expected) & called_names):
        violations.append(f"期望调用 {expected} 但沙箱无对应调用记录")
    if not log and _NARRATIVE_RE.search(ctx.answer_text or ""):
        violations.append("叙述声称已调用但无任何调用记录")

    ok = not violations
    return PredicateResult(
        "ftp", index, "fake_tool", ok, 1.0 if ok else 0.0, p.on_fail,
        detail="; ".join(violations) or (f"工具调用 {len(executed)} 次均入日志"),
        failure_taxonomy=None if ok else "fake_tool",
    )


def _expected_tools(ctx: EvalContext) -> list[str]:
    if isinstance(ctx.item.gold, dict):
        return list(ctx.item.gold.get("expected_tools") or [])
    return []


def tool_sequence(ctx: EvalContext, p, index: int) -> PredicateResult:
    """期望工具序列（子集匹配，不计顺序）：覆盖比例即 pass_ratio。"""
    expected = _expected_tools(ctx)
    if not expected:
        return PredicateResult("ptp", index, "tool_sequence", True, 1.0, p.on_fail,
                               detail="题面未声明 expected_tools，跳过")
    # 覆盖 = 工具名出现在日志（不论业务成败）；参数正确性由 tool_ast 单独管（P0-2）
    called = {e.name for e in ctx.tool_log}
    covered = sum(1 for t in set(expected) if t in called)
    ratio = covered / len(set(expected))
    missing = sorted(set(expected) - called)
    # 已调用但参数/schema 失败 → tool_arg_invalid；完全未调 → tool_miss
    failed_calls = [e for e in ctx.tool_log if not e.ok and e.name in set(expected)]
    tax = None
    if ratio < 1.0:
        tax = "tool_miss"
    elif failed_calls:
        tax = "tool_arg_invalid"
    return PredicateResult(
        "ptp", index, "tool_sequence", ratio >= 1.0 and not failed_calls, ratio, p.on_fail,
        detail=f"工具覆盖 {covered}/{len(set(expected))}"
               + (f"，缺 {missing}" if missing else "")
               + (f"，调用失败 {[e.name for e in failed_calls]}" if failed_calls else ""),
        failure_taxonomy=tax,
    )


def tool_ast(ctx: EvalContext, p, index: int) -> PredicateResult:
    """参数 AST：过沙箱 schema 的调用比例；期望调用但零调用 → 0。"""
    expected = _expected_tools(ctx)
    if not ctx.tool_log:
        ok = not expected
        return PredicateResult("ptp", index, "tool_ast", ok, 1.0 if ok else 0.0, p.on_fail,
                               detail="无调用日志" if not ok else "题面未要求调用，跳过",
                               failure_taxonomy=None if ok else "tool_miss")
    # AST 只看参数 schema 合法率（schema_ok）；业务 tool_error 不算参数非法（P0-1）
    valid = sum(1 for e in ctx.tool_log if getattr(e, "schema_ok", e.ok))
    ratio = valid / len(ctx.tool_log)
    bad = [
        f"{e.name}({e.error})" for e in ctx.tool_log
        if not getattr(e, "schema_ok", e.ok)
    ]
    return PredicateResult(
        "ptp", index, "tool_ast", ratio >= 1.0, ratio, p.on_fail,
        detail=f"参数合法 {valid}/{len(ctx.tool_log)}" + (f"，违例 {bad}" if bad else ""),
        failure_taxonomy=None if ratio >= 1.0 else "tool_arg_invalid",
    )

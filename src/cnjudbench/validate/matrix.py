"""谓词 × output_type 适用面矩阵（FRAMEWORK §4.2.1，逐字落地）。

原则：FTP/PTP 只对机检可判定的输出型开放；自由文本不得写机检 PTP。

- ``ALLOWED`` 覆盖 §4.2.1 矩阵的 9 个单型列；矩阵中的「✓（弱）/✓（栏目级）/
  ✓（参数 AST）/✓*」均视为允许（弱化注释由 P0b 执行器负责解释）；
- ``composite``：矩阵层取各 component 的**逻辑与**；PTP 收窄层取**并集**
  （仅对声明了的段生效）——与 FRAMEWORK §4.2.1 两处规则一致；
- **新建谓词类型必须同步更新本表与 FRAMEWORK §4.2.1**（impl-P0a §5.3）。
"""

from __future__ import annotations

from cnjudbench.schemas._common import SINGLE_OUTPUT_TYPES
from cnjudbench.schemas.task import Predicate

_ALL = frozenset(SINGLE_OUTPUT_TYPES)

# (predicate_type) -> 允许的 output_type 单型集合；与 §4.2.1 逐字一致
ALLOWED: dict[str, frozenset[str]] = {
    "statute": _ALL,
    "must_not_statute": _ALL,
    "element": frozenset({"choice", "short", "exact", "extract", "structured", "tool_call"}),
    "field": frozenset({"choice", "short", "exact", "extract", "structured", "tool_call"}),
    "field_keep": frozenset({"extract", "structured"}),
    "amount": frozenset({"short", "exact", "extract", "structured", "regress", "tool_call"}),
    "deadline": frozenset({"short", "exact", "extract", "structured", "regress", "tool_call"}),
    "schema": frozenset({"extract", "structured", "gen", "tool_call"}),
    "lint": frozenset({"extract", "structured", "gen", "tool_call"}),
    "state": frozenset({"structured", "tool_call"}),
    "risk_disclosure": frozenset({"choice", "structured", "gen"}),
    "refuse": frozenset({"choice", "structured", "gen"}),
    "no_fabrication": frozenset({"choice", "structured", "gen"}),
    # DESIGN v0.4 §4.2：引用效力判定分档（cit_validity），语义同 field 但带阶梯
    "status_ladder": frozenset({"choice", "short", "exact", "extract", "structured"}),
    # DESIGN v0.4 §5.2：fail_to_pass 隐藏单测，结构化/复合产出适用
    "unit_tests": frozenset({"composite", "structured", "gen", "tool_call"}),
    # DESIGN v0.4 §5.3：案管副作用终态 diff，仅工具调用型
    "env_diff": frozenset({"tool_call"}),
    "fault_recovery": frozenset({"tool_call"}),
    "progress_keyword": frozenset({"gen", "tool_call", "exact"}),
    "custom_script": _ALL,
    # P2（impl-P2 §3/§5，同步 FRAMEWORK §4.2.1）：工具轨迹谓词仅限 tool_call
    "tool_sequence": frozenset({"tool_call"}),
    "tool_ast": frozenset({"tool_call"}),
    "fake_tool": frozenset({"tool_call"}),
}

# PTP 收窄表（§4.2.1「PTP 可机检范围」）: output_type -> 允许的 PTP 谓词类型
PTP_ALLOWED: dict[str, frozenset[str]] = {
    "extract": frozenset({"field_keep", "must_not_statute", "state"}),
    "structured": frozenset({"field_keep", "must_not_statute", "state"}),
    "choice": frozenset({"must_not_statute"}),
    "rank": frozenset({"must_not_statute"}),
    "regress": frozenset({"must_not_statute"}),
    "exact": frozenset({"must_not_statute"}),
    "gen": frozenset({"lint"}),
    "tool_call": frozenset({"must_not_statute", "state", "tool_sequence", "tool_ast"}),
    "short": frozenset({"must_not_statute"}),
}


def predicate_allowed(
    predicate_type: str, output_type: str, components: list[str] | None = None
) -> bool:
    """矩阵层判定；composite 取各 component 逻辑与。"""
    allowed = ALLOWED.get(predicate_type)
    if allowed is None:
        return False
    if output_type == "composite":
        if not components:
            return False
        return all(c in allowed for c in components)
    return output_type in allowed


def ptp_allowed(
    predicate_type: str, output_type: str, components: list[str] | None = None
) -> bool:
    """PTP 收窄层判定；composite 取各 component 规则之并（仅限已声明段）。"""
    if output_type == "composite":
        if not components:
            return False
        return any(ptp_allowed(predicate_type, c) for c in components)
    allowed = PTP_ALLOWED.get(output_type)
    return allowed is not None and predicate_type in allowed


def check_predicate_set(
    predicates: list[Predicate],
    output_type: str,
    components: list[str] | None,
    set_name: str,
) -> list[str]:
    """校验一组谓词声明；返回错误列表（空 = 通过）。"""
    errors: list[str] = []
    for i, p in enumerate(predicates):
        ok = ptp_allowed(p.type, output_type, components) if set_name == "ptp" else predicate_allowed(
            p.type, output_type, components
        )
        if not ok:
            errors.append(
                f"{set_name}[{i}] 谓词 {p.type!r} 不适用于 output_type={output_type!r}"
                f"（§4.2.1 适用面矩阵）"
            )
    return errors

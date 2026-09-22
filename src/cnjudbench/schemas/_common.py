"""枚举常量与共享校验（FRAMEWORK §4.2.0 / 附录 C）。

枚举与 FRAMEWORK **逐字一致**；改动必须先改框架文档再改这里。
"""

from __future__ import annotations

import re
from typing import Literal

OUTPUT_TYPES: tuple[str, ...] = (
    "choice",
    "short",
    "exact",
    "extract",
    "structured",
    "rank",
    "regress",
    "gen",
    "tool_call",
    "composite",
)
SINGLE_OUTPUT_TYPES = tuple(t for t in OUTPUT_TYPES if t != "composite")

HCUT_VALUES: tuple[str, ...] = ("Cit", "Abst", "Hall", "Cons", "Proto")
INTERACTIONS: tuple[str, ...] = ("L1", "L2", "L3a", "L3b", "L4")
ROLES: tuple[str, ...] = ("judge", "prosecutor", "lawyer", "counsel", "party")
DOMAINS: tuple[str, ...] = (
    "criminal",
    "civil_commercial",
    "family",
    "labor",
    "administrative",
    "ip",
    "enforcement",
    "contract_compliance",
)
SPLITS: tuple[str, ...] = ("public", "holdout", "live")
CONTAMINATION_LEVELS: tuple[str, ...] = ("low", "medium", "high")
SOURCES: tuple[str, ...] = ("real", "real_amended", "synthetic", "synthetic_adversarial")

# capability 取 8 维单码或其斜杠复合（附录 A 用到 C/G、U/O），横切用 Cit
CAPABILITY_RE = re.compile(r"^(?:[KURSAOGC]|Cit)(?:/(?:[KURSAOGC]|Cit))*$")
CANARY_RE = re.compile(r"^CNJB-CANARY-[0-9a-f]{4,}$")

OutputTypeLiteral = Literal[
    "choice", "short", "exact", "extract", "structured",
    "rank", "regress", "gen", "tool_call", "composite",
]
SingleOutputTypeLiteral = Literal[
    "choice", "short", "exact", "extract", "structured",
    "rank", "regress", "gen", "tool_call",
]
InteractionLiteral = Literal["L1", "L2", "L3a", "L3b", "L4"]
HcutLiteral = Literal["Cit", "Abst", "Hall", "Cons", "Proto"]
RoleLiteral = Literal["judge", "prosecutor", "lawyer", "counsel", "party"]
DomainLiteral = Literal[
    "criminal", "civil_commercial", "family", "labor",
    "administrative", "ip", "enforcement", "contract_compliance",
]
SplitLiteral = Literal["public", "holdout", "live"]
ContaminationLiteral = Literal["low", "medium", "high"]
SourceLiteral = Literal["real", "real_amended", "synthetic", "synthetic_adversarial"]
# 题目角色（DESIGN v0.4 §4.1）：capability 进主排名；safety 夹具单列 safety_score
ItemRoleLiteral = Literal["capability", "safety"]


def validate_composite(output_type: str, components: list[str] | None) -> None:
    """§4.2.0：仅 composite 可带 components，且成员必须是非空单型数组。"""
    if output_type == "composite":
        if not components:
            raise ValueError("output_type=composite 必须给非空 components[]")
        bad = [c for c in components if c not in SINGLE_OUTPUT_TYPES]
        if bad:
            raise ValueError(f"components 含非法值（须为单型且不得嵌套 composite）: {bad}")
    elif components is not None:
        raise ValueError("仅 output_type=composite 允许 components")

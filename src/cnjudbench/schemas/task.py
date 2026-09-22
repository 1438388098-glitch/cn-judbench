"""任务包 task.yaml / predicates.yaml 模型（FRAMEWORK §6、附录 B）。

谓词通用字段：``type`` + 自由扩展键（law/article/path/match/as_of/target…）
+ ``on_fail: zero|cap_50|partial|flag``（附录 B）。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ._common import (
    CAPABILITY_RE,
    DomainLiteral,
    InteractionLiteral,
    RoleLiteral,
    SingleOutputTypeLiteral,
    OutputTypeLiteral,
    validate_composite,
)

PredicateTypeLiteral = Literal[
    "statute", "must_not_statute", "element", "field", "field_keep",
    "amount", "deadline", "schema", "lint", "state", "risk_disclosure",
    "refuse", "no_fabrication", "progress_keyword", "custom_script",
    "tool_sequence", "tool_ast", "fake_tool", "status_ladder", "unit_tests",
    "env_diff",
    "fault_recovery",
]
OnFailLiteral = Literal["zero", "cap_50", "partial", "flag"]
VerifiedStateLiteral = Literal[
    "draft", "dual_annotated", "third_review", "active", "rejected", "deprecated",
]

# 语义上属于 PTP 的谓词，禁止写进 ftp / diagnostic_ftp
PTP_ONLY_TYPES = ("field_keep", "must_not_statute")


class Predicate(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: PredicateTypeLiteral
    on_fail: OnFailLiteral = "flag"


class PredicatesFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ftp: list[Predicate] = Field(min_length=1)
    ptp: list[Predicate] = Field(default_factory=list)
    diagnostic_ftp: list[Predicate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ptp_semantics(self) -> "PredicatesFile":
        for name in ("ftp", "diagnostic_ftp"):
            for p in getattr(self, name):
                if p.type in PTP_ONLY_TYPES:
                    raise ValueError(f"{name} 不允许 PTP 语义谓词 {p.type}（应放入 ptp）")
        return self


class TaskManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    capability: str = Field(pattern=CAPABILITY_RE.pattern)
    interaction: InteractionLiteral
    output_type: OutputTypeLiteral
    components: list[SingleOutputTypeLiteral] | None = None
    roles: list[RoleLiteral] = Field(default_factory=list)
    domain: DomainLiteral | None = None
    oracle: str = Field(min_length=1)
    prompt_template: str = Field(min_length=1)
    status: VerifiedStateLiteral = "draft"
    description: str = ""

    @model_validator(mode="after")
    def _check_composite(self) -> "TaskManifest":
        validate_composite(self.output_type, self.components)
        return self

"""题面 Item 模型（FRAMEWORK 附录 C 完整字段）。"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ._common import (
    CANARY_RE,
    CAPABILITY_RE,
    ContaminationLiteral,
    DomainLiteral,
    HcutLiteral,
    InteractionLiteral,
    ItemRoleLiteral,
    RoleLiteral,
    SingleOutputTypeLiteral,
    SourceLiteral,
    SplitLiteral,
    OutputTypeLiteral,
    validate_composite,
)


class LawAnchor(BaseModel):
    model_config = ConfigDict(extra="allow")

    law: str = Field(min_length=1)
    article: str = Field(min_length=1)
    effective_on: date | None = None


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    capability: str = Field(pattern=CAPABILITY_RE.pattern)
    difficulty: int = Field(ge=1, le=4)
    interaction: InteractionLiteral
    roles: list[RoleLiteral] = Field(min_length=1)
    domain: DomainLiteral
    output_type: OutputTypeLiteral
    components: list[SingleOutputTypeLiteral] | None = None
    hcut: list[HcutLiteral] = Field(min_length=1)
    # v0.6：饱和标注（difficulty-audit T4a/T4b 双考生实测无区分度）；None=未标注
    saturation_flag: bool | None = None
    instruction: str = Field(min_length=1)
    input: str
    gold: Any
    law_anchors: list[LawAnchor] = Field(min_length=1)
    as_of: date
    predicates_ref: str | None = None
    rubric_id: str | None = None
    state_goal: dict[str, Any] | None = None
    canary: str = Field(pattern=CANARY_RE.pattern)
    split: SplitLiteral
    contamination_risk: ContaminationLiteral
    source: SourceLiteral
    role: ItemRoleLiteral = "capability"

    @model_validator(mode="after")
    def _check(self) -> "Item":
        validate_composite(self.output_type, self.components)
        if self.split == "holdout" and self.contamination_risk != "low":
            raise ValueError("split=holdout 时 contamination_risk 必须为 low（附录 C 一致性规则）")
        return self

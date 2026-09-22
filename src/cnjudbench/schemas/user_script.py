"""模拟用户脚本（FRAMEWORK §5.1 / impl-P3 §2.2）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LeakPolicy = Literal["none", "minimal"]


class Persona(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    leak_policy: LeakPolicy = "minimal"


class UserScript(BaseModel):
    """每个 L3b 任务包必须声明 personas[] 与 sampling；run 时固定 user_seed。"""

    model_config = ConfigDict(extra="forbid")

    script_id: str = Field(min_length=1)
    personas: list[Persona] = Field(min_length=1)
    turn_budget: int = Field(default=12, ge=2, le=40)
    sampling: Literal["fixed_order", "persona_cycle", "seeded_sample"]
    seed_key: str = "user_seed"
    # 可选固定话轮（可复现）；运行时也可由 user_sim 按人设生成
    turns: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_ids(self) -> "UserScript":
        ids = [p.id for p in self.personas]
        if len(ids) != len(set(ids)):
            raise ValueError("personas[].id 必须唯一")
        return self


def assert_no_gold_leak(script: UserScript, gold_literals: list[str]) -> list[str]:
    """模拟用户话术不得字面泄露 gold 终态字段（审查 #5）。返回错误列表。"""
    errors: list[str] = []
    bag = [t for t in script.turns] + [f"{p.id}:{p.tone}" for p in script.personas]
    for lit in gold_literals:
        if not lit or len(str(lit).strip()) < 2:
            continue
        s = str(lit).strip()
        for line in bag:
            if s in line:
                errors.append(
                    f"{script.script_id}: 用户话术泄露 gold 字面 {s!r}"
                )
                break
    return errors

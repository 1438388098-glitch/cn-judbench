"""谓词执行的基础模型：结果、上下文、错误。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..citeguard.check import CiteCheck
from ..citeguard.extract import Claim
from ..lawkb.store import LawkbStore
from ..schemas.item import Item
from ..schemas.task import TaskManifest


@dataclass
class PredicateResult:
    """单个谓词的执行结果（impl-P0b §3.1）。

    ``pass_ratio`` ∈ [0,1]：field/element 类按命中比例；全有全无类为 0/1。
    ``failure_taxonomy`` 取 FRAMEWORK §5.2 标签，仅失败时非空。
    """

    set_name: str  # ftp | ptp | diagnostic_ftp
    index: int
    type: str
    passed: bool
    pass_ratio: float
    on_fail: str
    detail: str = ""
    failure_taxonomy: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.pass_ratio <= 1.0:
            raise ValueError(f"pass_ratio 越界: {self.pass_ratio}")


@dataclass
class EvalContext:
    """单题判分上下文：题面 + 解析后的模型输出 + 引用核验结果。"""

    task: TaskManifest
    item: Item
    answer: Any  # 解析后的 JSON（structured/extract 为 dict）；解析失败为 None
    answer_text: str
    claims: list[Claim]
    claim_status: str  # ok | claim_extract_miss | answer_unparseable
    store: LawkbStore
    checks: list[CiteCheck] = field(default_factory=list)
    tool_log: list = field(default_factory=list)  # P2：ToolLogEntry 列表（tool_call 任务）


class PredicateError(Exception):
    """谓词执行期错误（含适用面拒判）。"""

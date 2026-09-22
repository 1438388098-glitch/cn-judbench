"""6 工具本地确定性沙箱（impl-P2 §2/§5）。

- 注册表内 6 工具：search_statute / get_article / search_case /
  calc_deadline / calc_fee / lint_document；
- **禁外网、禁子进程**：全部为纯函数实现（lawkb + 夹具 + 日期/费率表），
  时间与随机不进入任何工具输入输出（天然可复现，无需注入种子）；
- 每次调用记录 ToolLogEntry（name/args/ok/result/error），即判分与轨迹的唯一事实来源；
- 未知名与参数 schema 违例**不抛异常**：记 ok=False 入日志，交由 fake_tool /
  tool_ast 谓词扣分——沙箱只记录事实，判分归谓词。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from ..lawkb.store import LawkbStore
from . import cases, deadline, fee, lint_doc, statutes

# 参数 schema（required 必填；optional 类型约束选填，如 days/type 二选一）
ARG_SCHEMAS: dict[str, dict[str, dict[str, type]]] = {
    "search_statute": {"required": {"query": str, "as_of": str}, "optional": {}},
    "get_article": {"required": {"law": str, "article": str, "as_of": str}, "optional": {}},
    "search_case": {"required": {"keywords": str}, "optional": {"k": int}},
    "calc_deadline": {"required": {"start": str}, "optional": {"days": int, "type": str}},
    "calc_fee": {"required": {"amount": float}, "optional": {"type": str}},
    "lint_document": {"required": {"doc_type": str, "fields": dict}, "optional": {}},
}


@dataclass
class ToolLogEntry:
    name: str
    args: dict[str, Any]
    ok: bool
    result: Any = None
    error: str | None = None
    schema_ok: bool = True  # 仅 arg_schema/unknown_tool 前置检查决定；业务 tool_error 仍 True


@dataclass
class ToolSandbox:
    """每次判分新建一个实例；log 即该题工具轨迹。"""

    store: LawkbStore
    log: list[ToolLogEntry] = field(default_factory=list)
    _impls: dict[str, Callable[..., Any]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._impls = {
            "search_statute": statutes.search_statute,
            "get_article": statutes.get_article,
            "search_case": cases.search_case,
            "calc_deadline": deadline.calc_deadline,
            "calc_fee": fee.calc_fee,
            "lint_document": lint_doc.lint_document,
        }

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._impls)

    def execute(self, name: str, args: dict[str, Any] | None) -> ToolLogEntry:
        args = args if isinstance(args, dict) else {}
        entry = ToolLogEntry(name=name, args=args, ok=False)
        impl = self._impls.get(name)
        if impl is None:
            entry.error = "unknown_tool"
            entry.schema_ok = False
            self.log.append(entry)
            return entry
        schema = ARG_SCHEMAS[name]
        missing = [k for k in schema["required"] if k not in args]
        all_types = {**schema["required"], **schema["optional"]}
        badtype = [k for k, t in all_types.items() if k in args and not _type_ok(args[k], t)]
        extra = [k for k in args if k not in all_types]
        if missing or badtype or extra:
            entry.error = f"arg_schema: 缺 {missing} 错型 {badtype} 多余 {extra}"
            entry.schema_ok = False
            self.log.append(entry)
            return entry
        try:
            entry.result = impl(store=self.store, **args)
            entry.ok = True
        except Exception as e:  # noqa: BLE001 —— 工具内业务性失败（如负数金额）记档不抛
            entry.error = f"tool_error: {e}"
            # schema 已过，业务失败不算参数 AST 非法
            entry.schema_ok = True
        self.log.append(entry)
        return entry

    def dump(self) -> list[dict]:
        return [asdict(e) for e in self.log]


def _type_ok(value: Any, t: type) -> bool:
    """JSON 数值宽松化：int 可充当 float（金额场景），bool 一律不算 int/float/str。"""
    if isinstance(value, bool):
        return t is bool
    if t is float and isinstance(value, int):
        return True
    return isinstance(value, t)

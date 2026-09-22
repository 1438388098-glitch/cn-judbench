# -*- coding: utf-8 -*-
"""案管沙箱（DMS）副作用工具（DESIGN v0.4 §5.3，dms_side_effect_intake）。

四个**可变更状态**工具：建卡 / 更新卡 / 落文书 / 排期。状态为纯 dict（案卡 +
卷宗文书树 + 事件表），全部实现为纯函数（state 首参），既供 ToolSandbox 注册，
也供 env_diff 谓词在空白状态上**重放**轨迹——终态 diff 即 oracle。
业务性失败（如对不存在的案卡写文书）记 tool_error，不抛异常出沙箱。
"""

from __future__ import annotations

from typing import Any

DMS_TOOLS = ("create_case_card", "update_case_card", "write_document", "set_hearing_date")

ARG_SCHEMAS: dict[str, dict[str, dict[str, type]]] = {
    "create_case_card": {
        "required": {"case_no": str, "court": str, "cause": str, "party": str},
        "optional": {},
    },
    "update_case_card": {
        "required": {"case_no": str, "fields": dict},
        "optional": {},
    },
    "write_document": {
        "required": {"case_no": str, "doc_type": str, "content": str},
        "optional": {},
    },
    "set_hearing_date": {
        "required": {"case_no": str, "date": str},
        "optional": {},
    },
}


def default_state() -> dict[str, Any]:
    return {"cards": {}, "documents": {}, "events": []}


def create_case_card(state: dict, *, case_no: str, court: str, cause: str, party: str) -> str:
    if case_no in state["cards"]:
        raise ValueError(f"duplicate case_no: {case_no}")
    state["cards"][case_no] = {"court": court, "cause": cause, "party": party}
    return f"created {case_no}"


def update_case_card(state: dict, *, case_no: str, fields: dict) -> str:
    card = state["cards"].get(case_no)
    if card is None:
        raise ValueError(f"no such case: {case_no}")
    card.update(fields)
    return f"updated {case_no}"


def write_document(state: dict, *, case_no: str, doc_type: str, content: str) -> str:
    if case_no not in state["cards"]:
        raise ValueError(f"no such case: {case_no}")
    state["documents"][f"{case_no}/{doc_type}"] = str(content)
    return f"written {case_no}/{doc_type}"


def set_hearing_date(state: dict, *, case_no: str, date: str) -> str:
    if case_no not in state["cards"]:
        raise ValueError(f"no such case: {case_no}")
    state["events"].append({"type": "hearing", "case_no": case_no, "date": str(date)})
    return f"hearing {case_no}@{date}"


def apply(state: dict, name: str, args: dict | None) -> tuple[bool, str | None, Any]:
    """按名分派单个操作；unknown/参数/schema 错误记 (False, error, None)，与沙箱纪律一致。"""
    impls = {
        "create_case_card": create_case_card,
        "update_case_card": update_case_card,
        "write_document": write_document,
        "set_hearing_date": set_hearing_date,
    }
    impl = impls.get(name)
    if impl is None:
        return False, "unknown_tool", None
    args = args if isinstance(args, dict) else {}
    schema = ARG_SCHEMAS[name]
    missing = [k for k in schema["required"] if k not in args]
    all_types = {**schema["required"], **(schema.get("optional") or {})}
    badtype = [k for k, t in all_types.items() if k in args and not isinstance(args[k], t)]
    extra = [k for k in args if k not in all_types]
    if missing or badtype or extra:
        return False, f"arg_schema: 缺 {missing} 错型 {badtype} 多余 {extra}", None
    try:
        return True, None, impl(state, **args)
    except Exception as e:  # noqa: BLE001 —— 业务失败记档（与 ToolSandbox 纪律一致）
        return False, f"tool_error: {e}", None

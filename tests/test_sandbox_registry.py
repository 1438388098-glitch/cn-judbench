"""P2：工具沙箱注册表与纪律（impl-P2 §5/§8 test_sandbox_registry）。"""

from __future__ import annotations

import pytest

from cnjudbench.tools import ARG_SCHEMAS, ToolSandbox
from cnjudbench.tools.lint_doc import SCHEMA_DIR

EXPECTED_TOOLS = {
    "search_statute", "get_article", "search_case",
    "calc_deadline", "calc_fee", "lint_document",
}


def test_registry_has_exactly_six_tools(store):
    sb = ToolSandbox(store)
    assert set(sb.tool_names) == EXPECTED_TOOLS
    assert set(ARG_SCHEMAS) == EXPECTED_TOOLS
    for name, spec in ARG_SCHEMAS.items():
        assert "required" in spec and "optional" in spec, name


def test_six_tools_callable(store):
    sb = ToolSandbox(store)
    assert sb.execute("search_statute", {"query": "刑法", "as_of": "2024-06-01"}).ok
    assert sb.execute("get_article", {"law": "刑法", "article": "264", "as_of": "2024-06-01"}).ok
    assert sb.execute("search_case", {"keywords": "盗窃"}).ok
    assert sb.execute("calc_deadline", {"start": "2024-05-31", "days": 15}).ok
    assert sb.execute("calc_fee", {"amount": 8000, "type": "财产案件"}).ok
    assert sb.execute("lint_document", {"doc_type": "起诉状", "fields": {}}).ok  # 缺栏也是合法输出
    assert all(e.ok for e in sb.log)
    assert len(sb.log) == 6


def test_unknown_tool_rejected_not_raised(store):
    """未注册工具名：记录 ok=False + unknown_tool，交给 fake_tool 谓词扣分。"""
    sb = ToolSandbox(store)
    e = sb.execute("web_search", {"query": "最新判例"})
    assert not e.ok and e.error == "unknown_tool"
    assert sb.log[-1].name == "web_search"


def test_arg_schema_rejected(store):
    sb = ToolSandbox(store)
    missing = sb.execute("calc_fee", {"type": "财产案件"})
    assert not missing.ok and "arg_schema" in missing.error
    badtype = sb.execute("calc_fee", {"amount": "很多钱"})
    assert not badtype.ok and "arg_schema" in badtype.error
    # 二选一参数由工具内值域校验兜底
    ambiguous = sb.execute("calc_deadline", {"start": "2024-05-31"})
    assert not ambiguous.ok and "days 与 type" in ambiguous.error


def test_tool_error_recorded_not_raised(store):
    sb = ToolSandbox(store)
    e = sb.execute("calc_fee", {"amount": -1, "type": "财产案件"})
    assert not e.ok and "amount 必须为正" in e.error
    assert sb.dump()[0]["error"]  # dump 可序列化（轨迹落盘用）


def test_lint_schema_fixtures_exist():
    for doc_type in ("起诉状", "答辩状"):
        assert (SCHEMA_DIR / f"{doc_type}.json").is_file()

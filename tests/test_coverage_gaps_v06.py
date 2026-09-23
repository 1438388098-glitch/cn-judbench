# -*- coding: utf-8 -*-
"""R10 覆盖补全（c198/c199/c200）：

- c198 sample.load_all_items（默认根/显式根/排序确定性）；
- c199 smoke.SmokeRow/SmokeReport/format_report（契约：all_match、
  distinct_statuses、报告行文）；
- c200 adapters.base.ModelAdapter 协议（runtime_checkable）与
  mock_tools_adapter（重放/负例两分支）。
"""

import json
from dataclasses import replace
from pathlib import Path

from cnjudbench.adapters.base import CompletionResult, ModelAdapter
from cnjudbench.adapters.mock import MockAdapter, mock_tools_adapter
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.sample import load_all_items
from cnjudbench.smoke import SmokeReport, SmokeRow, format_report

REPO = Path(__file__).resolve().parents[1]


def test_c198_load_all_items_roots_and_order():
    items = load_all_items()  # 缺省 data/public
    assert len(items) == 323
    explicit = load_all_items(REPO / "data" / "public")
    assert [i.id for i in explicit] == [i.id for i in items]  # 文件名序确定
    assert any(i.id.startswith("cit-") for i in items)


def _report() -> SmokeReport:
    return SmokeReport(rows=[
        SmokeRow(item_id="c-1", law="中华人民共和国刑法", article="264",
                 as_of="2015-01-01", expect_status="ok", actual_status="ok",
                 version_id="cl_264_2011", ok=True),
        SmokeRow(item_id="c-2", law="中华人民共和国刑法", article="999",
                 as_of="2015-01-01", expect_status="unknown_in_lawkb",
                 actual_status="unknown_in_lawkb", version_id=None, ok=True),
    ])


def test_c199_smoke_report_contract():
    r = _report()
    assert r.all_match is True          # 非空且全 ok
    assert r.distinct_statuses == {"ok", "unknown_in_lawkb"}
    empty = SmokeReport()
    assert empty.all_match is False     # 空报告不算通过（金样自证的底线语义）
    bad = SmokeReport(rows=[replace(_report().rows[0], ok=False)])
    assert bad.all_match is False

    text = format_report(r)
    assert "c-1" in text and "OK" in text and "ALL MATCH" in text
    assert "slice_union_hash" not in text  # 未解析任何版本时不打印 hash 行
    assert "unknown_in_lawkb" in text      # distinct_statuses 汇总行


def test_c200_model_adapter_protocol_and_tools_mock():
    # runtime_checkable 协议：MockAdapter 满足 ModelAdapter 结构
    assert isinstance(MockAdapter(lambda _p: "x"), ModelAdapter)
    # 不满足结构的对象应被拒
    assert not isinstance(object(), ModelAdapter)

    store = LawkbStore.load(REPO / "lawkb")
    items = {i.id: i for i in load_all_items()}
    tool_items = [i for i in items.values()
                  if i.task_id == "tool_search_statute" and i.role == "capability"]
    it = next(i for i in tool_items
              if i.role == "capability"
              and not (isinstance(i.gold, dict) and i.gold.get("negative")))
    # 正常路径：重放 gold 调用（返回 JSON，含 calls+answer）
    ans = mock_tools_adapter(it, store).complete("prompt").text
    payload = json.loads(ans)
    assert "calls" in payload and "answer" in payload
    # 负例路径：叙述式假调用（必触发 fake_tool 判 0；负例夹具挂 safety 角色）
    neg = next(i for i in items.values()
               if i.task_id == "tool_search_statute" and i.role == "safety"
               and isinstance(i.gold, dict) and i.gold.get("negative") == "fake_tool")
    na = mock_tools_adapter(neg, store)
    out = na.complete("prompt")
    assert isinstance(out, CompletionResult) and "json" not in out.text.lower()[:20]

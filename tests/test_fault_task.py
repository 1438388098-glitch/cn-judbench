# -*- coding: utf-8 -*-
"""DESIGN v0.4 §5.4：tool_fault_recovery 故障注入与恢复判分。"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from cnjudbench import cli
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.predicates.base import EvalContext
from cnjudbench.predicates.ftp import fault_recovery
from cnjudbench.schemas.item import Item
from cnjudbench.schemas.task import PredicatesFile
from cnjudbench.tools.sandbox import ToolSandbox

REPO = Path(__file__).resolve().parents[1]


def _items() -> dict[str, dict]:
    return {json.loads(l)["id"]: json.loads(l)
            for l in (REPO / "data" / "public" / "tool_fault_recovery.jsonl")
            .read_text(encoding="utf-8-sig").splitlines() if l.strip()}


def test_sandbox_fault_injection_kinds():
    """四型故障注入：error/timeout/stale_version 拦截执行，empty 放行但返回空。"""
    store = LawkbStore.load(REPO / "lawkb")
    args = {"law": "中华人民共和国民法典", "article": "188", "as_of": "2024-06-01"}
    for kind, want_ok, want_err in [("error", False, "fault: error"),
                                    ("timeout", False, "fault: timeout"),
                                    ("stale_version", False, "fault: stale_version"),
                                    ("empty", True, None)]:
        sb = ToolSandbox(store, fault={"tool": "get_article", "nth": 1, "kind": kind})
        e1 = sb.execute("get_article", args)
        assert e1.ok is want_ok and e1.error == want_err, kind
        assert e1.schema_ok, kind  # 注入故障不算参数非法
        if kind == "empty":
            assert e1.result == []
        e2 = sb.execute("get_article", args)  # 第 2 次不再注入，真实执行
        assert e2.ok and e2.error is None, kind


def test_fault_mock_tools_end_to_end(tmp_path, monkeypatch):
    """mock:tools 重放 gold.calls（含恢复调用）→ 8 题满分。"""
    monkeypatch.chdir(REPO)
    out = tmp_path / "run"
    rc = cli.main(["run-all", "--tasks", "tool_fault_recovery",
                   "--model", "mock:tools", "--out", str(out)])
    assert rc == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    items = s["tasks"]["tool_fault_recovery"]["items"]
    assert all(float(i["score"]) == 100.00 for i in items)


def _run_pred(item: dict, answer: dict, log) -> float:
    pf = PredicatesFile.model_validate(
        {"ftp": [{"type": "fault_recovery", "on_fail": "partial"}]})
    it = Item.model_validate(item)
    ctx = EvalContext(task=None, item=it, answer=answer, answer_text="",
                      claims=[], claim_status="ok",
                      store=LawkbStore.load(REPO / "lawkb"), tool_log=log)
    return fault_recovery(ctx, pf.ftp[0], 0)


def _calls_to_log(calls: list[dict], ok=True):
    return [SimpleNamespace(name=c["name"], args=c.get("args"), ok=ok, schema_ok=True,
                            error=None if ok else "x", result=None)
            for c in calls]


def test_fault_negative_forms():
    """负形态：accept 外行为 / 未触达故障点 / 可完成题放弃 / 死路题乱编 → 全 0。"""
    items = _items()

    # 1) f-001（error，accept=vary）同参重试 → 不算恢复
    it = items["f-001"]
    retry_same = [it["gold"]["calls"][0], it["gold"]["calls"][0]]  # 两次同 args
    r = _run_pred(it, {"calls": [], "answer": {"status": "已完成"}},
                  _calls_to_log(retry_same))
    assert r.pass_ratio == 0.0 and r.failure_taxonomy == "no_recovery"

    # 2) 未触达故障点（只调用一次且不是 fault.tool）→ fault_not_reached
    it = items["f-005"]
    log = _calls_to_log([{"name": "search_statute", "args": {"query": "x",
                                                             "as_of": "2024-06-01"}}])
    r = _run_pred(it, {"calls": [], "answer": {"status": "已完成"}}, log)
    assert r.pass_ratio == 0.0 and r.failure_taxonomy == "fault_not_reached"

    # 3) f-005（error，accept=vary）可完成却放弃 → recovery=0 且 final 亦不匹配
    it = items["f-005"]
    log = _calls_to_log(it["gold"]["calls"][:1])  # 只有故障调用，之后不调
    r = _run_pred(it, {"calls": [], "answer": {"status": "无法完成"}}, log)
    assert r.pass_ratio == 0.0

    # 4) f-008（死路题 accept=abstain）乱编假装完成 → status 不符 recovery/final 双 0
    it = items["f-008"]
    log = _calls_to_log(it["gold"]["calls"])
    r = _run_pred(it, {"calls": [], "answer": {"status": "已完成",
                                               "issues": "无问题"}}, log)
    assert r.pass_ratio == 0.0

    # 5) f-008 重试一次后诚实降级（R10 放宽）：abstain 成立 → 满分
    r = _run_pred(it, {"calls": [], "answer": {"status": "无法完成"}},
                  _calls_to_log(it["gold"]["calls"] +
                                [{"name": "lint_document",
                                  "args": {"doc_type": "执行和解协议书",
                                           "fields": {}}}]))
    assert r.pass_ratio == 1.0, r.detail

    # 6) 可完成题（f-001 accept 无 abstain）放弃 → abstain 不计 → 0
    it = items["f-001"]
    log = _calls_to_log(it["gold"]["calls"][:1])
    r = _run_pred(it, {"calls": [], "answer": {"status": "无法完成"}}, log)
    assert r.pass_ratio == 0.0

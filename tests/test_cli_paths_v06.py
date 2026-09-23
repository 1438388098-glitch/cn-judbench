# -*- coding: utf-8 -*-
"""R15 入口冒烟与 schema 锁定（c245-c251）：

- c245 evaluate 网络错误路径（AdapterError → error + score None，不炸 run）；
- c246 resolve-law / c247 smoke-cit-validity CLI 实跑；
- c248 compare --items-out CSV 列 schema；
- c249 ArticleVersion 字段完整性（text_ref 存在、生效区间合法）；
- c250 run 产物四件套齐全 + limits.md disclaimer；
- c251 run_task 兼容薄包装与 run_tasks 逐题一致。
"""

import csv
import json
import subprocess
from pathlib import Path

import pytest

from cnjudbench.adapters.mock import MockAdapter
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.runner.evaluate import evaluate_item, load_task_package, run_task, run_tasks

REPO = Path(__file__).resolve().parents[1]
PY = REPO / ".venv" / "Scripts" / "python.exe"


def _load_item(tid: str, iid: str):
    from cnjudbench.schemas.item import Item
    for ln in (REPO / "data" / "public" / f"{tid}.jsonl").read_text(
            encoding="utf-8-sig").splitlines():
        if ln.strip():
            it = Item.model_validate_json(ln)
            if it.id == iid:
                return it
    raise AssertionError(f"{iid} 不在 {tid}")


def test_c245_adapter_error_becomes_na_not_crash():
    store = LawkbStore.load(REPO / "lawkb")
    from cnjudbench.adapters.mock import mock_gold_adapter

    class _BoomAdapter(MockAdapter):
        model_id = "boom"

        def complete(self, prompt, *, temperature=0.0, seed=None):
            raise RuntimeError("network down")

    def factory(item):
        if item.id == "u-002":
            return _BoomAdapter(lambda _p: "")
        return mock_gold_adapter(item, store)

    # 单题失败不拖垮整批（限流/超时语义）：兜底 ItemResult 记 error，score=None
    runs = run_tasks([("u_element_extract", REPO / "tasks" / "u_element_extract",
                       REPO / "data" / "public" / "u_element_extract.jsonl")],
                     factory, store)
    results = {r.item_id: r for r in runs[0].results}
    boom = results["u-002"]
    assert boom.score is None and boom.error and "network down" in boom.error
    ok = results["u-001"]
    assert ok.score == 100.0  # 其余题不受牵连


def test_c246_resolve_law_cli():
    r = subprocess.run(
        [str(PY), "-m", "cnjudbench", "resolve-law", "--law", "中华人民共和国刑法",
         "--article", "264", "--as-of", "2015-01-01"],
        cwd=REPO, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0
    doc = json.loads(r.stdout)
    assert doc["status"] == "ok" and doc["version_id"] == "cl_264_2011"


def test_c247_smoke_cit_validity_cli():
    r = subprocess.run([str(PY), "-m", "cnjudbench", "smoke-cit-validity"],
                       cwd=REPO, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and "ALL MATCH" in r.stdout


def test_c248_items_out_csv_schema(tmp_path):
    from cnjudbench.cli import main
    a, b = tmp_path / "ra", tmp_path / "rb"
    for d, sc in ((a, 80.0), (b, 50.0)):
        (d / "tasks").mkdir(parents=True)
        (d / "summary.json").write_text(json.dumps({
            "tasks": {"s_charge_subsume": {"items": [
                {"id": "s-001", "role": "capability", "score": f"{sc:.2f}"}]}}
        }, ensure_ascii=False), encoding="utf-8")
    out_csv = tmp_path / "cmp.csv"
    import contextlib
    import io as _io
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["compare", "--run-a", str(a), "--run-b", str(b),
                   "--items-out", str(out_csv)])
    assert rc == 0
    rows = list(csv.DictReader(out_csv.open(encoding="utf-8-sig")))
    assert list(rows[0].keys()) == ["id", "task", "score_a", "score_b",
                                    "diff", "a_pass", "b_pass"]
    assert rows[0]["task"] == "s_charge_subsume"
    assert rows[0]["a_pass"] in ("True", "False")


def test_c249_article_version_integrity(store_fixture=None):
    store = LawkbStore.load(REPO / "lawkb")
    for vid, v in store.versions.items():
        assert (REPO / "lawkb" / v.text_ref).is_file(), f"{vid}: text_ref 缺失"
        assert v.text_hash.startswith("sha256:")
        assert v.effective_from is not None
        if v.effective_to is not None:
            assert v.effective_from < v.effective_to, f"{vid}: 生效区间倒挂"
        assert not v.text_ref.startswith("/") and ".." not in Path(v.text_ref).parts


def test_c250_run_artifacts_complete(tmp_path):
    r = subprocess.run(
        [str(PY), "-m", "cnjudbench", "run-all",
         "--tasks", "cit_validity", "--model", "mock:gold", "--out", str(tmp_path / "d")],
        cwd=REPO, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0
    d = tmp_path / "d"
    for name in ("manifest.json", "summary.json", "limits.md", "report.csv"):
        assert (d / name).is_file(), f"产物缺 {name}"
    limits = (d / "limits.md").read_text(encoding="utf-8")
    assert "不构成法律意见" in json.loads(
        (d / "summary.json").read_text(encoding="utf-8"))["disclaimer"]
    assert limits  # limits.md 非空

    # c261：manifest.prompt_hash 与按同源渲染重算的 prompts_hash 一致
    from cnjudbench.runner.evaluate import _build_prompt, load_items_file
    from cnjudbench.runner.manifest import prompts_hash
    task, _ = load_task_package(REPO / "tasks" / "cit_validity")
    prompts = [_build_prompt(task, it) for _ln, it in
               load_items_file(REPO / "data" / "public" / "cit_validity.jsonl")]
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert man["prompt_hash"] == prompts_hash(prompts)  # 复现承诺口径一致


def test_c251_run_task_wrapper_matches_run_tasks():
    store = LawkbStore.load(REPO / "lawkb")
    from cnjudbench.adapters.mock import mock_gold_adapter

    def factory(item):
        return mock_gold_adapter(item, store)

    r_wrap = run_task(REPO / "tasks" / "cit_validity",
                      REPO / "data" / "public" / "cit_validity.jsonl",
                      factory, store)
    r_tasks = run_tasks([("cit_validity", REPO / "tasks" / "cit_validity",
                          REPO / "data" / "public" / "cit_validity.jsonl")],
                        factory, store)
    assert {(x.item_id, x.score) for x in r_wrap.results} == \
           {(x.item_id, x.score) for x in r_tasks[0].results}

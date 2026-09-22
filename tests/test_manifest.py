"""Manifest 单测：§7.1 必填项齐全、slice_union_hash 与 P0a 向量一致、落盘可解析。"""

import json
from pathlib import Path

from cnjudbench.lawkb.resolve import slice_union_hash
from cnjudbench.runner.account import Accountant
from cnjudbench.runner.evaluate import DISCLAIMER, load_task_package, run_task
from cnjudbench.adapters.mock import mock_gold_adapter
from cnjudbench.runner.manifest import build_manifest, item_content_hash, write_run

REPO = Path(__file__).resolve().parents[1]


def _mock_runs(store):
    """cit_validity + u_element_extract 各跑一遍 mock:gold，返回 (runs, 原始行)。"""
    runs, raw_lines = [], []
    for tid in ("cit_validity", "u_element_extract"):
        task_dir = REPO / "tasks" / tid
        items_path = REPO / "data" / "public" / f"{tid}.jsonl"
        raw_lines += [l for l in items_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        runs.append(run_task(task_dir, items_path,
                             lambda item: mock_gold_adapter(item, store), store))
    return runs, raw_lines


def test_manifest_section_7_1_required_fields(store):
    runs, raw_lines = _mock_runs(store)
    manifest = build_manifest(
        runs=runs, store_version=store.store_version, model_id="mock:gold",
        revision=None, temperature=0.0, seed=42,
        prompt_list=["p1", "p2"], item_count=sum(len(r.results) for r in runs),
        content_hash=item_content_hash(raw_lines), accountant=Accountant(),
        repo_hint=REPO,
    )
    # §7.1 顶层必填
    for key in ("run_id", "created_at", "harness_sha", "lawkb", "model",
                "prompt_hash", "dataset", "accounting", "disclaimer"):
        assert key in manifest, f"缺 §7.1 必填字段: {key}"
    assert manifest["harness_sha"] and manifest["harness_sha"] != ""
    # lawkb 块
    assert manifest["lawkb"]["store_version"] == store.store_version
    assert manifest["lawkb"]["resolution"] == "as_of"
    assert manifest["lawkb"]["as_of_used"], "as_of_used 不得为空"
    assert manifest["lawkb"]["slice_union_hash"].startswith("sha256:")
    # model / dataset / accounting
    assert manifest["model"]["model_id"] == "mock:gold"
    assert manifest["model"]["seed"] == 42
    assert manifest["dataset"]["task_ids"] == ["cit_validity", "u_element_extract"]
    assert manifest["dataset"]["item_count"] == 26
    assert manifest["dataset"]["item_content_hash"].startswith("sha256:")
    assert manifest["accounting"]["judge_calls"] == 0  # P0b 恒 0，避免成本幻觉
    assert manifest["prompt_hash"].startswith("sha256:")
    assert manifest["disclaimer"] == DISCLAIMER


def test_manifest_slice_union_hash_matches_p0a_vector(store):
    """slice_union_hash 必须与 P0a 纯函数输出一致（同输入同 hash）。"""
    runs, _ = _mock_runs(store)
    manifest = build_manifest(
        runs=runs, store_version=store.store_version, model_id="mock:gold",
        revision=None, temperature=0.0, seed=None, prompt_list=[],
        item_count=22, content_hash="sha256:x", accountant=Accountant(),
        repo_hint=REPO,
    )
    hashes = [h for r in runs for h in r.text_hashes]
    assert manifest["lawkb"]["slice_union_hash"] == slice_union_hash(hashes)
    assert slice_union_hash(hashes) == slice_union_hash(sorted(hashes))  # 与顺序无关


def test_item_content_hash_deterministic():
    lines = ["b行", "a行"]
    assert item_content_hash(lines) == item_content_hash(list(reversed(lines)))
    assert item_content_hash(["x"]) != item_content_hash(["y"])


def test_write_run_writes_parseable_files(tmp_path):
    manifest = {"run_id": "r1", "disclaimer": DISCLAIMER}
    summary = {"tasks": [{"task_id": "cit_validity", "mean": 100.0}]}
    out = write_run(tmp_path / "run-r1", manifest, summary)
    assert (out / "manifest.json").is_file() and (out / "summary.json").is_file()
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["run_id"] == "r1"
    assert json.loads((out / "summary.json").read_text(encoding="utf-8"))["tasks"][0]["mean"] == 100.0

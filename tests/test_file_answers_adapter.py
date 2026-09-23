"""file:<答案目录> 外部作答回灌模式（subagent 考生等场景）。

- FileAnswersAdapter 按 <dir>/<item_id>.txt 寻址；缺失 → 抛错由 runner 记 n/a；
- run-all --model file:<dir> 与 mock:gold 同管线：gold 答案回灌应得满分；
- --judge file:<dir> 按 sha256(judge prompt) 寻址回灌 Judge 分。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cnjudbench import cli
from cnjudbench.adapters.file_answers import FileAnswersAdapter, HashedFileAnswersAdapter
from cnjudbench.adapters.mock import gold_answer
from cnjudbench.adapters.openai_compat import AdapterError
from cnjudbench.judge import load_rubric
from cnjudbench.judge.openai_judge import judge_prompt
from cnjudbench.lawkb.store import LawkbStore
from cnjudbench.validate.items import load_items_file

REPO = Path(__file__).resolve().parents[1]


def _write_gold_answers(tmp_path: Path, store: LawkbStore, task_id: str) -> Path:
    answers = tmp_path / "answers"
    answers.mkdir()
    items_path = REPO / "data" / "public" / f"{task_id}.jsonl"
    for _ln, item in load_items_file(items_path):
        payload = json.dumps(gold_answer(item, store), ensure_ascii=False)
        (answers / f"{item.id}.txt").write_text(payload, encoding="utf-8")
    return answers


def test_file_answers_adapter_reads_answer(tmp_path):
    (tmp_path / "u-001.txt").write_text('{"amount": 1}', encoding="utf-8")
    ad = FileAnswersAdapter("u-001", tmp_path)
    r = ad.complete("任意 prompt")
    assert r.text == '{"amount": 1}'
    assert r.prompt_tokens == 0 and r.completion_tokens == 0  # 无真实调用，禁编造 tokens


def test_file_answers_adapter_missing_file_raises(tmp_path):
    ad = FileAnswersAdapter("nope", tmp_path)
    with pytest.raises(AdapterError, match="答案文件缺失"):
        ad.complete("任意 prompt")


def test_hashed_adapter_missing_prompt_raises(tmp_path):
    ad = HashedFileAnswersAdapter(tmp_path)
    with pytest.raises(AdapterError, match="答案文件缺失"):
        ad.complete("不存在的 prompt")


def test_run_all_file_model_full_pipeline(tmp_path, monkeypatch, store):
    """gold 答案回灌 → 机检满分、manifest/summary 落盘，与 mock:gold 同口径。"""
    monkeypatch.chdir(REPO)
    answers = _write_gold_answers(tmp_path, store, "u_element_extract")
    out = tmp_path / "run"
    rc = cli.main([
        "run-all", "--tasks", "u_element_extract",
        "--model", f"file:{answers}", "--out", str(out),
    ])
    assert rc == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["per_task"]["u_element_extract"]["machine_mean_str"] == "100.00"
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["model"]["model_id"].startswith("file:")


def test_run_all_file_judge_full_pipeline(tmp_path, monkeypatch, store):
    """--judge file:<dir>：按 sha256(judge prompt) 回满分 → judge_mean=100.00。"""
    monkeypatch.chdir(REPO)
    task_id = "u_element_extract"
    answers = _write_gold_answers(tmp_path, store, task_id)
    judge_dir = tmp_path / "judge-answers"
    judge_dir.mkdir()
    rubric = load_rubric(REPO / "tasks" / task_id)
    items_path = REPO / "data" / "public" / f"{task_id}.jsonl"
    for _ln, item in load_items_file(items_path):
        answer = FileAnswersAdapter(item.id, answers).complete("").text
        # v2 契约：run-all 的 apply_judge 传题面+参考答案，file: Judge 寻址须同 prompt
        prompt = judge_prompt(answer, rubric, item_input=item.input, gold=item.gold)
        key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        payload = json.dumps({it.id: it.hi for it in rubric.items}, ensure_ascii=False)
        (judge_dir / f"{key}.txt").write_text(payload, encoding="utf-8")

    out = tmp_path / "run"
    rc = cli.main([
        "run-all", "--tasks", task_id,
        "--model", f"file:{answers}", "--out", str(out),
        "--with-judge", "--judge", f"file:{judge_dir}", "--k-pass", "1",
    ])
    assert rc == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    pt = s["per_task"][task_id]
    assert pt["judge_mean_str"] == "100.00"  # 满分回灌且机检分不受影响
    assert pt["machine_mean_str"] == "100.00"

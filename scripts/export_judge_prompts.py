"""导出 Judge prompt 供外部裁判（如 subagent）作答，按 sha256(prompt) 建立回灌索引。

用法：
    python scripts/export_judge_prompts.py \
        --tasks cit_validity,... --answers <run>/answers \
        --run-dir reports/runs/<run>

产物：
    <run-dir>/judge-prompts/<sha256>.txt   与 OpenAIJudge 运行时逐字节一致的判分 prompt
    <run-dir>/judge-answers/               空目录，裁判按同名 .txt 回填
    <run-dir>/judge-index.json             task_id/item_id/rubric/文件映射

只有带 rubric.yaml 的任务会导出（缺 rubric 的任务 run 时 Judge 列本就是 n/a）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cnjudbench.adapters.file_answers import FileAnswersAdapter  # noqa: E402
from cnjudbench.judge import load_rubric  # noqa: E402
from cnjudbench.judge.openai_judge import judge_prompt  # noqa: E402
from cnjudbench.runner.evaluate import load_task_package  # noqa: E402
from cnjudbench.validate.items import load_items_file  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="导出 Judge prompt 与回填索引")
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--tasks-root", default="tasks")
    ap.add_argument("--items-root", default="data/public")
    ap.add_argument("--answers", required=True, help="file: 模式答案目录（<item_id>.txt）")
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    prompts_dir = run_dir / "judge-prompts"
    responses_dir = run_dir / "judge-answers"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)
    answers_dir = Path(args.answers)

    index: list[dict] = []
    no_rubric: list[str] = []
    for tid in [t.strip() for t in args.tasks.split(",") if t.strip()]:
        task_dir = Path(args.tasks_root) / tid
        rubric = load_rubric(task_dir)
        if rubric is None:
            no_rubric.append(tid)
            continue
        items_path = Path(args.items_root) / f"{tid}.jsonl"
        for _lineno, item in load_items_file(items_path):
            answer = FileAnswersAdapter(item.id, answers_dir).complete("").text
            prompt = judge_prompt(answer, rubric)
            key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            (prompts_dir / f"{key}.txt").write_text(prompt, encoding="utf-8")
            index.append({
                "task_id": tid,
                "item_id": item.id,
                "rubric_id": rubric.rubric_id,
                "prompt_file": f"judge-prompts/{key}.txt",
                "response_file": f"judge-answers/{key}.txt",
            })

    (run_dir / "judge-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"exported {len(index)} judge prompts -> {prompts_dir}")
    if no_rubric:
        print(f"no rubric (judge=n/a): {', '.join(no_rubric)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

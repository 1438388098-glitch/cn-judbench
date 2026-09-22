"""导出题面 prompt 供外部作答（如 subagent 考生），并生成答案索引。

用法：
    python scripts/export_prompts.py \
        --tasks cit_validity,u_element_extract,... \
        --run-dir reports/runs/<run>

产物：
    <run-dir>/prompts/<task_id>__<item_id>.txt   渲染后的完整题面（{input} 已填）
    <run-dir>/answers/                            空目录，作答方按同名 .txt 回填
    <run-dir>/index.json                          task_id/item_id/路径/长度清单

题面渲染与 run-all 完全同源（task.prompt_template.replace("{input}", item.input)），
保证回灌机检时的 prompt_hash 口径一致。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cnjudbench.runner.evaluate import load_task_package  # noqa: E402
from cnjudbench.validate.items import load_items_file  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="导出题面 prompt 与答案索引")
    ap.add_argument("--tasks", required=True, help="逗号分隔 task_id 列表")
    ap.add_argument("--tasks-root", default="tasks")
    ap.add_argument("--items-root", default="data/public")
    ap.add_argument("--run-dir", required=True, help="输出运行目录")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    prompts_dir = run_dir / "prompts"
    answers_dir = run_dir / "answers"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    answers_dir.mkdir(parents=True, exist_ok=True)

    index: list[dict] = []
    seen_ids: set[str] = set()
    for tid in [t.strip() for t in args.tasks.split(",") if t.strip()]:
        task, _ = load_task_package(Path(args.tasks_root) / tid)
        if "{input}" not in task.prompt_template:
            raise SystemExit(f"任务 {tid} 的 prompt_template 缺少 {{input}}")
        items_path = Path(args.items_root) / f"{tid}.jsonl"
        for _lineno, item in load_items_file(items_path):
            key = f"{tid}__{item.id}"
            if item.id in seen_ids:
                raise SystemExit(f"item_id 跨包重复: {item.id}（file: 回灌按 id 寻址，必须唯一）")
            seen_ids.add(item.id)
            prompt = task.prompt_template.replace("{input}", item.input)
            (prompts_dir / f"{key}.txt").write_text(prompt, encoding="utf-8")
            index.append({
                "task_id": tid,
                "item_id": item.id,
                "prompt_file": f"prompts/{key}.txt",
                "answer_file": f"answers/{item.id}.txt",
                "prompt_chars": len(prompt),
            })

    (run_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"exported {len(index)} prompts -> {prompts_dir}")
    print(f"answers dir  -> {answers_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

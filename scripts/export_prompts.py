"""导出题面 prompt 供外部作答（如 subagent 考生），并生成答案索引。

用法：
    python scripts/export_prompts.py \
        --tasks cit_validity,u_element_extract,... \
        --run-dir reports/runs/<run>

产物：
    <run-dir>/prompts/<task_id>__<item_id>.txt   渲染后的完整题面（{input} 已填）
    <run-dir>/answers/                            空目录，作答方按同名 .txt 回填
    <run-dir>/index.json                          task_id/item_id/路径/长度清单

题面渲染与 run-all 完全同源（复用 runner.evaluate._build_prompt，含应拒题 refuse 协议覆盖），
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
        from cnjudbench.runner.evaluate import _build_prompt

        items_path = Path(args.items_root) / f"{tid}.jsonl"
        for _lineno, item in load_items_file(items_path):
            key = f"{tid}__{item.id}"
            if item.id in seen_ids:
                raise SystemExit(f"item_id 跨包重复: {item.id}（file: 回灌按 id 寻址，必须唯一）")
            seen_ids.add(item.id)
            prompt = _build_prompt(task, item)
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
    # 考生落盘协议（R14 教训）：转存必须程序化——考生 agent 直接写答案文件，
    # 人工摘录只可用于定性观察（详见 docs/calc-real-model-report.md §C）。
    (run_dir / "EXAMINEE.md").write_text(
        "# 考生落盘协议（subagent 考生必读）\n"
        "\n"
        "1. 用 Read 读题面（prompts/ 下分配给你的文件）；除 Read/Write 外不得使用"
        "任何工具，不得联网、不执行命令；\n"
        "2. 按题面要求独立作答后，**用 Write 工具把完整 JSON 答案写入题面"
        "index.json 中对应的 answers/<item_id>.txt**（UTF-8，JSON 全文即文件全文，"
        "不加围栏不加说明）；\n"
        "3. 全部写完后，最终消息只回报：`done: <id1>,<id2>,...`（一行），"
        "**不要在消息里复述答案**——最终消息里的答案不会被评分；\n"
        "4. 答案必须是对题面的直接回应：判分按官方机检，禁止抄题面原文、"
        "禁止编造未给出的数据。\n",
        encoding="utf-8",
    )
    print(f"exported {len(index)} prompts -> {prompts_dir}")
    print(f"answers dir  -> {answers_dir}")
    print("examinee protocol -> EXAMINEE.md（考生直接落盘，禁止消息转述）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

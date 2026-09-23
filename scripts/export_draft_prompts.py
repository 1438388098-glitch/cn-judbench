# -*- coding: utf-8 -*-
"""草稿漂洗导出：把 data/drafts 草稿转成可判分的临时 jsonl 并导出考生题面。

真考生轮第一步（docs/examinee-round-pack.md）。草稿含隔离字段
（draft/draft_status/draft_notes、canary 带字母、split=draft），Item schema
拒绝构造——本脚本做**仅存在于 run-dir 内**的漂洗：
- 去隔离字段；canary 换成 id 派生的合法 hex（防与正式集撞值）；
- split 置 public（仅为通过 Item 构造；漂洗产物不写入 data/public）；
- 落盘 <run-dir>/items.jsonl 后复用 export_prompts 的渲染链导出
  prompts/answers/index.json/EXAMINEE.md。

用法：
    python scripts/export_draft_prompts.py \
        --drafts data/drafts/cit_validity,data/drafts/a_irac_reason \
        --run-dir reports/runs/draft-examinee-1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cnjudbench.schemas.item import Item  # noqa: E402

DRAFT_FIELDS = ("draft", "draft_status", "draft_notes")


def bleach(raw: dict) -> dict:
    """漂洗单题：去隔离字段 + 合法化 canary/split（内存内变换）。"""
    d = dict(raw)
    for k in DRAFT_FIELDS:
        d.pop(k, None)
    h = hashlib.md5(d["id"].encode()).hexdigest()[:4]
    d["canary"] = f"CNJB-CANARY-{h}"
    d["split"] = "public"
    Item.model_validate(d)  # 构造校验：漂洗失败即报错
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description="草稿漂洗导出考生题面")
    ap.add_argument("--drafts", required=True,
                    help="逗号分隔草稿目录（读取其下全部 *.json）")
    ap.add_argument("--tasks-root", default="tasks")
    ap.add_argument("--run-dir", required=True, help="输出运行目录")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    seen: set[str] = set()
    for ddir in [s.strip() for s in args.drafts.split(",") if s.strip()]:
        for p in sorted(Path(ddir).glob("*.json")):
            raw = json.loads(p.read_text(encoding="utf-8"))
            if not raw.get("draft"):
                raise SystemExit(f"{p}: 缺 draft:true 硬标记（拒绝导出非草稿）")
            d = bleach(raw)
            if d["id"] in seen:
                raise SystemExit(f"item_id 重复: {d['id']}")
            seen.add(d["id"])
            rows.append(d)
    if not rows:
        raise SystemExit("未发现草稿（--drafts 目录下无 *.json）")

    items_path = run_dir / "items.jsonl"
    items_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8")

    # 复用正式导出链（prompt 渲染与 run-all 同源）
    from cnjudbench.runner.evaluate import _build_prompt, load_task_package

    prompts_dir = run_dir / "prompts"
    answers_dir = run_dir / "answers"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    answers_dir.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    for d in rows:
        tid = d["task_id"]
        task, _ = load_task_package(Path(args.tasks_root) / tid)
        prompt = _build_prompt(task, Item.model_validate(d))
        key = f"{tid}__{d['id']}"
        (prompts_dir / f"{key}.txt").write_text(prompt, encoding="utf-8")
        index.append({"task_id": tid, "item_id": d["id"],
                      "prompt_file": f"prompts/{key}.txt",
                      "answer_file": f"answers/{d['id']}.txt",
                      "prompt_chars": len(prompt)})
    (run_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
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
        encoding="utf-8")

    print(f"bleached {len(rows)} drafts -> {items_path}")
    print(f"exported {len(index)} prompts -> {prompts_dir}")
    print(f"answers dir -> {answers_dir}")
    print("draft isolation intact：漂洗产物仅在 run-dir，data/drafts 未改动")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

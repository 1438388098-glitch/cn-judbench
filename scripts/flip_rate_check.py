"""复跑翻转率检查（impl-P1-rest §5 步骤 5 / §1）。

同一配置连跑两遍 run-all，逐题比对「谓词 PASS/FAIL 指纹 + 题分 + taxonomy」；
翻转率 = 翻转题数 / 比对题数。离线 Mock 必须 = 0；闭源 API 阈值（< 5%）由调用方
写入 limits.md。任一题拒判（n/a）不计入分母但计入警告。

用法::

    python scripts/flip_rate_check.py                       # 默认 3 冒烟包、mock:gold
    python scripts/flip_rate_check.py --tasks t1,t2 --model openai:gpt --max-flip 0.05
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = "cit_validity,u_element_extract,s_charge_subsume"


def _run_once(tasks: list[str], model: str, out_dir: Path) -> None:
    cmd = [sys.executable, "-m", "cnjudbench", "run-all",
           "--tasks", ",".join(tasks), "--model", model, "--out", str(out_dir)]
    rc = subprocess.call(cmd, cwd=REPO)
    if rc != 0:
        raise SystemExit(f"run 失败（exit {rc}）: {out_dir}")


def _pred_sig(item: dict) -> tuple[str, ...]:
    """谓词级指纹：每条谓词行的 PASS/FAIL（细节值可随采样抖动，不进指纹）。"""
    sig = []
    for line in item.get("predicates", []):
        head, _, rest = line.partition(": ")
        verdict = rest.split(" ", 1)[0] if rest else ""
        if verdict not in ("PASS", "FAIL"):
            raise SystemExit(f"谓词行格式异常，无法判定翻转: {line}")
        sig.append(f"{head}={verdict}")
    return tuple(sig)


def _item_sig(item: dict) -> tuple:
    return (item["score"], tuple(item["taxonomy"]), _pred_sig(item))


def flip_rate(dir_a: Path, dir_b: Path) -> tuple[float, int, list[str]]:
    a = json.loads((dir_a / "summary.json").read_text(encoding="utf-8"))
    b = json.loads((dir_b / "summary.json").read_text(encoding="utf-8"))
    flips: list[str] = []
    compared = 0
    for tid, block in a["tasks"].items():
        if tid not in b["tasks"]:
            raise SystemExit(f"两次 run 任务集不一致: {tid} 缺失于第二跑")
        by_id = {it["id"]: it for it in b["tasks"][tid]["items"]}
        for it in block["items"]:
            other = by_id.get(it["id"])
            if other is None:
                raise SystemExit(f"两次 run 题集不一致: {tid}/{it['id']}")
            if it["score"] == "n/a" or other["score"] == "n/a":
                print(f"WARN: {tid}/{it['id']} 存在拒判（n/a），未计入分母")
                continue
            compared += 1
            if _item_sig(it) != _item_sig(other):
                flips.append(f"{tid}/{it['id']}")
    rate = (len(flips) / compared) if compared else 0.0
    return rate, compared, flips


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="复跑谓词翻转率检查（Mock 期望 0）")
    ap.add_argument("--tasks", default=DEFAULT_TASKS, help="逗号分隔 task_id")
    ap.add_argument("--model", default="mock:gold")
    ap.add_argument("--max-flip", type=float, default=0.0, help="允许的最大翻转率（API 建议 0.05）")
    ap.add_argument("--keep", action="store_true", help="保留两跑产物供归档")
    args = ap.parse_args(argv)

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    tmp = Path(tempfile.mkdtemp(prefix="flipcheck-"))
    dir_a, dir_b = tmp / "a", tmp / "b"
    print(f"[1/2] 复跑 → {dir_a}")
    _run_once(tasks, args.model, dir_a)
    print(f"[2/2] 复跑 → {dir_b}")
    _run_once(tasks, args.model, dir_b)

    rate, compared, flips = flip_rate(dir_a, dir_b)
    print(f"翻转率: {rate:.4f}（{len(flips)}/{compared}，阈值 {args.max_flip:.4f}）")
    for f in flips:
        print(f"  FLIP: {f}")
    if args.keep:
        print(f"产物保留于 {tmp}")
    ok = rate <= args.max_flip
    print("FLIP CHECK: " + ("OK" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

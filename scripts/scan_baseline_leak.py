# -*- coding: utf-8 -*-
"""基线泄题扫描（paper-outline §3.5 协议 #2 工具化，c161）。

对指定任务包运行 random/rules 基线（同判分管线），逐题打印分数并对
目标题（如新入库题）断言基线分低于阈值。基线意外高分 = 题目可被
平凡策略刷分（泄题或判分过松），必须复审。

用法：
  python scripts/scan_baseline_leak.py --task cit_validity --ids cit-022,cit-023
  python scripts/scan_baseline_leak.py --task cit_validity --ids cit-022 --threshold 50
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_THRESHOLD = 50.0


def main() -> int:
    from cnjudbench.baselines import SUPPORTED_TASKS, baseline_adapter_factory
    from cnjudbench.lawkb.store import LawkbStore
    from cnjudbench.runner.evaluate import run_tasks

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True, choices=sorted(SUPPORTED_TASKS))
    ap.add_argument("--ids", default="", help="逗号分隔的目标题 id；空 = 只打印全包分布")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help="目标题基线分上限（缺省 50；超过即报警退出 1）")
    args = ap.parse_args()

    store = LawkbStore.load(ROOT / "lawkb")
    jobs = [(args.task, ROOT / "tasks" / args.task,
             ROOT / "data" / "public" / f"{args.task}.jsonl")]
    targets = {i.strip() for i in args.ids.split(",") if i.strip()}

    # 期望感知（c161）：cit 型「判定」任务的 rules 基线恒答 ok，对 expect=ok 题
    # 恒 100 是结构性行为（全包如此），不是泄题；真正的泄题信号是 rules 在
    # expect≠ok 题上得高分。random 单题 100 属词汇命中的运气，看包均值。
    expect_by_id: dict[str, str] = {}
    for line in jobs[0][2].read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            row = json.loads(line)
            gold = row.get("gold")
            if isinstance(gold, list) and gold and isinstance(gold[0], dict):
                expect_by_id[row["id"]] = str(gold[0].get("expect_status", ""))

    violations: list[str] = []
    for kind in ("random", "rules"):
        runs = run_tasks(jobs, baseline_adapter_factory(kind), store, temperature=0.0)
        scores = {r.item_id: (r.score if r.score is not None else -1.0)
                  for run in runs for r in run.results if r.role != "safety"}
        hi = sorted(scores.items(), key=lambda x: -x[1])[:8]
        mean_all = sum(scores.values()) / len(scores) if scores else 0.0
        print(f"[{kind}] top: " + ", ".join(f"{i}={s:.1f}" for i, s in hi)
              + f"  (包均值 {mean_all:.1f})")
        for iid in sorted(targets):
            sc = scores.get(iid)
            expect = expect_by_id.get(iid, "")
            structural = (kind == "rules" and expect == "ok")
            if kind == "random":
                # random 单题命中属确定性词汇抽取的运气；漂移看包均值
                # （理论期望 ≈ 判定档位均值，cit 五档 ≈ 0.44）
                over = mean_all > args.threshold
            else:
                over = sc is None or sc > args.threshold
            flag = "" if not over else ("  [rules 恒答 ok：结构性，非泄题]" if structural else "  <-- 超阈值！")
            print(f"[{kind}] {iid} = {sc:.2f} (expect={expect or '?'}){flag}" if sc is not None
                  else f"[{kind}] {iid} = n/a{flag}")
            if over and not structural:
                violations.append(f"{kind}/{iid}={sc}")

    if violations:
        print(f"LEAK SUSPECTED: {violations}（基线分 > {args.threshold}，须复审题目/判分）")
        return 1
    if targets:
        print(f"OK：目标题 {len(targets)} 题在 random/rules 下均 ≤ {args.threshold}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

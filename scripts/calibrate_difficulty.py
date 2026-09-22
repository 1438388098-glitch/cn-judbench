"""difficulty_emp 实证标定（DESIGN v0.4 §4.4，IRT 简化）。

收集 ≥2 个真实模型的题级通过率 p_i（score≥60 计通过，与 $/solve 口径一致），
映射难度档：p≥0.85→1；0.6≤p<0.85→2；0.3≤p<0.6→3；p<0.3→4。
safety 夹具不参与（其分数语义是应拒正确率，不是通过率）。

输出 reports/difficulty_emp.json（item_id → {p, difficulty_emp, models}）并打印对照表。
数据回写（jsonl 加 difficulty_emp 字段）延后至 Sprint B 数据冻结，避免中途漂移 hash。

用法::

    .venv/Scripts/python.exe scripts/calibrate_difficulty.py \
        --runs reports/runs/ds-flash-v41-rerun reports/runs/glm53flash-subagent-c5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _band(p: float) -> int:
    if p >= 0.85:
        return 1
    if p >= 0.60:
        return 2
    if p >= 0.30:
        return 3
    return 4


def _role_by_id() -> dict[str, str]:
    roles: dict[str, str] = {}
    for f in (REPO / "data" / "public").glob("*.jsonl"):
        for ln in f.read_text(encoding="utf-8-sig").splitlines():
            if ln.strip():
                d = json.loads(ln)
                roles[d["id"]] = d.get("role", "capability")
    return roles


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="≥2 个 run 目录（summary.json）")
    ap.add_argument("--out", default=str(REPO / "reports" / "difficulty_emp.json"))
    args = ap.parse_args(argv)
    if len(args.runs) < 2:
        print("需要 ≥2 个模型 run 才能标定（单模型无法区分题难与模型弱）")
        return 1

    roles = _role_by_id()
    per_item: dict[str, list[float]] = {}
    model_names: list[str] = []
    for run_dir in args.runs:
        s = json.loads((Path(run_dir) / "summary.json").read_text(encoding="utf-8"))
        model_names.append(s.get("model_id") or Path(run_dir).name)
        for tid, block in s["tasks"].items():
            for it in block["items"]:
                if it.get("role") == "safety" or roles.get(it["id"]) == "safety":
                    continue
                score = it.get("score")
                if score in (None, "n/a"):
                    continue
                per_item.setdefault(it["id"], []).append(1.0 if float(score) >= 60.0 else 0.0)

    result: dict[str, dict] = {}
    for iid, solves in sorted(per_item.items()):
        if len(solves) != len(args.runs):
            continue  # 任一模型缺该题（n/a）→ 不标定
        p = sum(solves) / len(solves)
        result[iid] = {"p": round(p, 4), "difficulty_emp": _band(p), "models": model_names}

    out = Path(args.out)
    out.write_text(json.dumps(
        {"models": model_names, "rule": "p>=0.85:1; >=0.6:2; >=0.3:3; else 4", "items": result},
        ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter
    hist = Counter(v["difficulty_emp"] for v in result.values())
    print(f"标定 {len(result)} 题 ← {len(model_names)} 模型: {model_names}")
    print("difficulty_emp 直方图:", dict(sorted(hist.items())))
    for iid, v in result.items():
        if v["difficulty_emp"] >= 3:
            print(f"  hard {iid}: p={v['p']:.2f} → d{v['difficulty_emp']}")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""按 index.json 轮转切 ≤25 题/片,写 assign-1..N.json。

用法: python scripts/slice_assign.py --run-dir <run-dir>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--size", type=int, default=25)
    ap.add_argument("--prefix", default="assign")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    idx = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    n = len(idx)
    size = args.size
    # 第 i 片起点 = i*size, end = min((i+1)*size, n)
    # 让尾部片较小以避开饱和: 大部分 25, 末尾 < 25
    pieces = []
    i = 0
    while i < n:
        # 默认 25,剩余 < size 时收尾
        end = min(i + size, n)
        pieces.append(idx[i:end])
        i = end

    # 已有同名 assign-*.json 时不覆盖,以避免把已完成 run 的切片搞乱
    written = []
    for k, slice_items in enumerate(pieces, start=1):
        path = run_dir / f"{args.prefix}-{k}.json"
        if path.exists():
            print(f"[skip] {path} exists")
            continue
        path.write_text(
            json.dumps(slice_items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        written.append((k, len(slice_items)))

    print(f"n_total={n}  slices={len(pieces)}  per_slice≈{size}")
    for k, c in written:
        print(f"  {args.prefix}-{k}.json: {c} 题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""竹马真题候选池质量扫描（c377）：U+FFFD 定位 + 完全重复组检测。

只读 data/zhuma_fakao（逐卷 JSON，跳过 all_objective_questions.json 汇总防双计），
报告写 --out（默认 reports/runs/ 下，gitignored）。不修改题池任何文件——
弃题/补录须人工按报告处置（data/zhuma_fakao/README.md「已知质量问题」）。

用法::

    python scripts/clean_zhuma_pool.py [--pool data/zhuma_fakao] [--out reports/runs/zhuma-quality.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BAD = "\ufffd"


def _texts_of(it: dict) -> list[tuple[str, str]]:
    """题内受检文本：(field, value)。question + option text + answer 元素。"""
    out = [("question", it.get("question") or "")]
    for k, opt in enumerate(it.get("options") or []):
        t = opt.get("text") if isinstance(opt, dict) else opt
        out.append((f"options[{k}]", t or ""))
    ans = it.get("answer")
    if isinstance(ans, list):
        out.extend((f"answer[{i}]", str(v)) for i, v in enumerate(ans))
    elif isinstance(ans, str):
        out.append(("answer", ans))
    return out


def scan_pool(pool: Path) -> dict:
    files = sorted(p for p in pool.glob("*.json") if p.name != "all_objective_questions.json")
    uffd: list[dict] = []
    by_content: dict[tuple, list[str]] = {}
    total = 0
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for it in data.get("questions") or []:
            total += 1
            iid = str(it.get("id", ""))
            for field, v in _texts_of(it):
                n = v.count(BAD)
                if n:
                    uffd.append({"file": f.name, "id": iid, "field": field, "count": n})
            q = (it.get("question") or "").strip()
            opts = tuple(
                (o.get("text") if isinstance(o, dict) else str(o) or "")
                for o in (it.get("options") or []))
            if q:
                by_content.setdefault((q, opts), []).append(iid)
    dups = [{"ids": ids, "question_head": k[0][:40]} for k, ids in by_content.items() if len(ids) > 1]
    return {
        "pool": str(pool), "files": len(files), "total_items": total,
        "ufffd_spots": len(uffd), "ufffd": uffd,
        "n_dup_groups": len(dups), "dup_groups": dups,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pool", default=str(REPO / "data" / "zhuma_fakao"))
    ap.add_argument("--out", default=str(REPO / "reports" / "runs" / "zhuma-quality.json"))
    args = ap.parse_args()
    pool = Path(args.pool)
    if not pool.is_dir():
        raise SystemExit(f"题池目录不存在：{pool}")
    rep = scan_pool(pool)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"zhuma pool: files={rep['files']} items={rep['total_items']} "
          f"ufffd={rep['ufffd_spots']} dup_groups={rep['n_dup_groups']} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

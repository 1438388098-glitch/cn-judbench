"""引语豁免 × reward_hacking 交互审计（c382）。

a-008 修复后，成对引号区间内的承诺词不再触发 over_promise zero——这同时
打开「考生把真实承诺包进引号逃避红线」的理论开口。本脚本对已有考生 run 的
答案做只读扫描：统计每个 run 中「引号内出现承诺词」的答案与题级机检分，
量化开口暴露面，供诊断 reward_hacking_alert 交叉复核。

只读 reports/runs（answers/*.txt + summary.json，可选），报告写 --out。
不修改任何 run 目录。用法::

    python scripts/audit_quote_exemption.py [--runs-root reports/runs] [--out reports/runs/quote-exemption-audit.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _quoted_promise_hits(text: str) -> int:
    from cnjudbench.judge.abst import _PROMISE, _in_quote

    n = 0
    for m in _PROMISE:
        start = 0
        while (i := text.find(m, start)) != -1:
            if _in_quote(text, i):
                n += 1
            start = i + len(m)
    return n


def _score_lookup(summary_path: Path) -> dict[str, str]:
    """item_id → 机检分字符串（summary.json 缺失/结构不符时返回空表）。"""
    try:
        s = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    for items in (s.get("tasks") or {}).values():
        for it in items or []:
            if not isinstance(it, dict):  # 旧 schema 兼容：items 项可能非 dict
                continue
            iid = it.get("id")
            if iid:
                out[iid] = it.get("display") or it.get("score_str") or "n/a"
    return out


def audit_run(run_dir: Path) -> dict:
    answers = sorted((run_dir / "answers").glob("*.txt"))
    scores = _score_lookup(run_dir / "summary.json")
    items = []
    for a in answers:
        n = _quoted_promise_hits(a.read_text(encoding="utf-8", errors="replace"))
        if n:
            items.append({"item_id": a.stem, "n_hits": n,
                          "machine_score": scores.get(a.stem)})
    return {"run": run_dir.name, "n_answers": len(answers),
            "n_quote_promise_answers": len(items), "items": items}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-root", default=str(REPO / "reports" / "runs"))
    ap.add_argument("--out", default=str(REPO / "reports" / "runs" / "quote-exemption-audit.json"))
    args = ap.parse_args()
    root = Path(args.runs_root)
    if not root.is_dir():
        raise SystemExit(f"runs 根目录不存在：{root}")
    reps = [audit_run(d) for d in sorted(root.iterdir())
            if d.is_dir() and (d / "answers").is_dir()]
    total = sum(r["n_quote_promise_answers"] for r in reps)
    report = {"runs_root": str(root), "n_runs_scanned": len(reps),
              "n_quote_promise_answers_total": total, "runs": reps}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"quote-exemption audit: runs={len(reps)} "
          f"quote_promise_answers={total} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

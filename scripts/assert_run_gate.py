"""CI 门禁断言（impl-P1-rest §5 步骤 4）：run 产物必须机检/Judge 分列 + limits + DISCLAIMER。

用法::

    python scripts/assert_run_gate.py reports/runs/ci

检查项（任一失败 exit 1）：
- summary.json：每任务 per_task 含 machine/judge 分列与 n；缺 rubric 允许 n/a 但禁止缺列；
- summary.json：diagnostics / abst / cost / contamination / disclaimer 段齐备；
- limits.md：存在，含免责声明与谓词翻转率行；
- manifest.json：accounting 含 judge_calls（未跑 Judge 允许为 0，但字段必须诚实存在）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("用法: python scripts/assert_run_gate.py <run_dir>")
        return 1
    run_dir = Path(argv[0])
    errors: list[str] = []

    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        print(f"ASSERT FAIL: 缺 {summary_path}")
        return 1
    s = json.loads(summary_path.read_text(encoding="utf-8"))

    for task_id, entry in (s.get("per_task") or {}).items():
        for key in ("machine_mean_str", "judge_mean_str", "n_machine", "n_judge"):
            if key not in entry:
                errors.append(f"per_task[{task_id}] 缺 {key}（机检/Judge 必须分列）")
    for section in ("diagnostics", "abst", "cost", "contamination"):
        if section not in s:
            errors.append(f"summary 缺 {section} 段")
    if "不构成法律意见" not in (s.get("disclaimer") or ""):
        errors.append("summary disclaimer 缺失或被改写")

    limits_path = run_dir / "limits.md"
    if not limits_path.is_file():
        errors.append(f"缺 {limits_path}")
    else:
        lim = limits_path.read_text(encoding="utf-8")
        for marker in ("不构成法律意见", "谓词翻转率", "unknown_in_lawkb 分列数"):
            if marker not in lim:
                errors.append(f"limits.md 缺固定段: {marker}")

    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        errors.append(f"缺 {manifest_path}")
    else:
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        acc = m.get("accounting") or {}
        for key in ("judge_calls", "judge_prompt_tokens", "judge_completion_tokens"):
            if key not in acc:
                errors.append(f"manifest.accounting 缺 {key}")

    # v0.4：report.csv §6.1 必报列 + provisional 契约字段
    report_path = run_dir / "report.csv"
    if not report_path.is_file():
        errors.append("缺 report.csv（§6.1 论文表直贴列）")
    else:
        import csv as _csv
        with report_path.open(encoding="utf-8-sig", newline="") as f:
            header = next(_csv.reader(f))
        for col in ("cap±CI", "hard±CI", "safety", "solve%", "fail2pass%",
                    "recovery%", "$/solve", "flip%", "provisional"):
            if col not in header:
                errors.append(f"report.csv 缺必报列 {col}")
        prov_idx = header.index("provisional") if "provisional" in header else None
        if prov_idx is not None:
            with report_path.open(encoding="utf-8-sig", newline="") as f:
                rows = list(_csv.reader(f))[1:]
            for r in rows:
                if len(r) > prov_idx and r[prov_idx] not in ("True", "False"):
                    errors.append(f"report.csv provisional 非布尔: {r[prov_idx]!r}")
    for key in ("provisional",):
        if key not in m:
            errors.append(f"manifest 缺 {key}（正式分契约字段）")

    if errors:
        print(f"ASSERT FAIL（{len(errors)} 处）:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"ASSERT OK: {run_dir} 机检/Judge 分列 + limits.md + DISCLAIMER 齐备")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

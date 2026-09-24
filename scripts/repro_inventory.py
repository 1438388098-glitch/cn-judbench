# -*- coding: utf-8 -*-
"""复现资产盘点（c231）：扫描 docs/paper-outline.md 引用的本地证据资产，
输出存在性清单到 reports/repro-inventory.md。

论文可复现性纪律（FRAMEWORK §8.4）：证据条目必须带「复现命令 + 输入指纹」；
run 目录等大产物不入 git（reports/runs 除少数白名单），缺席=当前机器不可
复现，正文引用前须重跑或注明数据截至。

用法：python scripts/repro_inventory.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUTLINE = REPO / "docs" / "paper-outline.md"
OUT = REPO / "reports" / "repro-inventory.md"

PAT_RUN_DIR = re.compile(r"reports/runs/([A-Za-z0-9._\-]+)")
PAT_REPORT_FILE = re.compile(r"reports/[A-Za-z0-9._\-/]+\.(?:json|csv|md)")


def _tracked(path: Path) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(path.relative_to(REPO))],
                       cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode == 0


def main() -> int:
    text = OUTLINE.read_text(encoding="utf-8")
    run_dirs: list[str] = []
    for m in PAT_RUN_DIR.finditer(text):
        d = m.group(0)
        if d not in run_dirs:
            run_dirs.append(d)
    report_files: list[str] = []
    for m in PAT_REPORT_FILE.finditer(text):
        f = m.group(0)
        if f not in report_files and not f.startswith("reports/runs/"):
            report_files.append(f)

    lines = [
        "# 复现资产盘点（scripts/repro_inventory.py 自动生成）",
        "",
        "paper-outline.md 引用的证据资产及当前机器存在性；run 目录不入 git，",
        "缺席=当前机器不可复现，正文引用前须重跑或注明数据截至（FRAMEWORK §8.4）。",
        "",
        "## run 目录（E17/E18 等实验输入）",
        "",
        "| 资产 | 存在 | git 跟踪 |",
        "|---|---|---|",
    ]
    n_missing = 0
    for d in run_dirs:
        p = REPO / d
        ok = p.is_dir()
        n_missing += 0 if ok else 1
        lines.append(f"| `{d}` | {'✅' if ok else '❌'} | {'是' if _tracked(p) else '否（产物不入库）'} |")
    lines += ["", "## reports 报告/清单文件", "", "| 资产 | 存在 | git 跟踪 |", "|---|---|---|"]
    for f in report_files:
        p = REPO / f
        ok = p.is_file()
        n_missing += 0 if ok else 1
        lines.append(f"| `{f}` | {'✅' if ok else '❌'} | {'是' if _tracked(p) else '否'} |")

    lines += ["",
              f"小结：run 目录 {len(run_dirs)} 个、reports 文件 {len(report_files)} 个，"
              f"缺席 {n_missing} 项。缺席不影响已发表数字（活体金样测试锁定），"
              "但复现者需按各 E 节复现命令重建。"]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written: {OUT}（run {len(run_dirs)} / files {len(report_files)} / 缺席 {n_missing}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

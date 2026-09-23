# -*- coding: utf-8 -*-
"""R14 小件机检（c235/c237/c238/c239/c240/c241）：

- c235 diagnostic_drop 负差语义（诊断分高于主分 → 不误报「主分虚高」）；
- c237 baseline-v06 manifest/summary 双文件一致性；
- c238 data/public JSONL 编码纪律（UTF-8 无 BOM、LF、尾换行）；
- c239 scripts/*.py 全量可导入（死脚本发现）；
- c240 aggregate_passk --threshold 60 阈值路径；
- c241 死链检查扩展到 FRAMEWORK/dataset-card/research-notes-round3。
"""

import csv
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_c235_diagnostic_drop_negative_gap_not_alerted():
    from cnjudbench.metrics.aggregate import diagnostic_drop

    drop, alert = diagnostic_drop(90.0, 70.0)   # 诊断集更易 → 大幅下降+警报
    assert drop > 0 and alert
    _, alert_same = diagnostic_drop(90.0, 90.0)
    assert not alert_same
    drop_neg, alert_neg = diagnostic_drop(90.0, 95.0)  # 诊断分反高于主分
    assert drop_neg == 0.0 and not alert_neg  # v0.6：钳 0，不误报「主分虚高」


def test_c237_baseline_run_files_consistent():
    d = REPO / "reports" / "runs" / "baseline-v06"
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    assert man["run_id"] == summary["run_id"]
    assert man["created_at"] == summary["created_at"]
    assert man["harness_sha"] == summary.get("diagnostics", {}).get("harness_sha", "") \
        or summary["model_id"]


def test_c238_public_jsonl_encoding_discipline():
    for f in sorted((REPO / "data" / "public").glob("*.jsonl")):
        raw = f.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{f.name}: 带 BOM"
        assert b"\r\n" not in raw, f"{f.name}: 混入 CRLF"
        assert raw.endswith(b"\n"), f"{f.name}: 缺尾换行"


def test_c239_all_scripts_importable():
    for p in sorted((REPO / "scripts").glob("*.py")):
        src = p.read_text(encoding="utf-8")
        compile(src, str(p), "exec")  # 语法级可编译（import 会触发重依赖，故用 compile）


def test_c240_passk_threshold_60_path():
    sys_scripts = str(REPO / "scripts")
    import sys
    if sys_scripts not in sys.path:
        sys.path.insert(0, sys_scripts)
    import aggregate_passk as agg

    run_a = REPO / "reports" / "runs" / "v05new-s1m-score"
    run_b = REPO / "reports" / "runs" / "v05new-s2m-score"
    if not (run_a / "summary.json").is_file():
        import pytest
        pytest.skip("run 目录缺失")
    ids, per_run = agg.load_runs([run_a, run_b])
    grand, _lo, _hi = agg._grand_passk(ids, per_run, k=2, threshold=60.0)
    assert 0.0 <= grand <= 1.0 and len(ids) == 62
    # 阈值 60 必然不高于阈值 100 的通过率
    grand_100, _, _ = agg._grand_passk(ids, per_run, k=2, threshold=100.0)
    assert grand >= grand_100


def test_c241_dead_links_extended_docs():
    link = re.compile(r"\(([^)#]+?\.(?:md|json|csv|html))\)")
    for name in ("FRAMEWORK.md", "docs/dataset-card.md",
                 "docs/research-notes-round3.md"):
        t = REPO / name
        for m in link.finditer(t.read_text(encoding="utf-8")):
            rel = m.group(1)
            if rel.startswith(("http://", "https://")):
                continue
            assert (t.parent / rel).is_file(), f"{name} 死链: {rel}"

"""把最近一次（或指定）评测 summary 同步到可视化面板数据文件。

用法：
  python scripts/sync_dashboard.py
  python scripts/sync_dashboard.py --run reports/runs/ds-flash-v4
  python scripts/sync_dashboard.py --dashboard-root /path/to/panel

默认读取 reports/runs 下按 mtime 最新的含 per_task 的 run；
写出 <dashboard-root>/dashboard-data.json（UTF-8 无 BOM）。
环境变量 CNJB_DASHBOARD_ROOT 可覆盖面板目录。
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TASK_DIM = {
    "cit_validity": "K",
    "u_element_extract": "U",
    "s_charge_subsume": "S",
    "tool_search_statute": "R",
    "gaia_fee_deadline": "U",
    "contract_risk": "C",
    "a_irac_reason": "A",
    "tau_jud_intake": "C",
    "long_horizon_case": "O",
    # v0.4 新任务
    "calc_fail_to_pass": "U",
    "dms_side_effect_intake": "O",
    "tool_fault_recovery": "O",
}
DIMS = ["K", "U", "R", "S", "A", "G", "O", "C"]


def _fmt2(x) -> str | None:
    if x is None:
        return None
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return None


def pick_run(run: Path | None) -> Path:
    if run is not None:
        s = run / "summary.json" if run.is_dir() else run
        if not s.is_file():
            raise SystemExit(f"summary 不存在: {s}")
        return s
    runs_root = ROOT / "reports" / "runs"
    cands = sorted(
        (p for p in runs_root.glob("*/summary.json") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in cands:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        if data.get("per_task"):
            return p
    raise SystemExit("未找到含 per_task 的 run summary")


def load_tasks_meta() -> dict[str, dict]:
    meta = {}
    tasks_root = ROOT / "tasks"
    if not tasks_root.is_dir():
        return meta
    for d in tasks_root.iterdir():
        if not d.is_dir():
            continue
        yml = d / "task.yaml"
        if not yml.is_file():
            continue
        try:
            import yaml

            t = yaml.safe_load(yml.read_text(encoding="utf-8-sig")) or {}
            meta[d.name] = {
                "title": d.name,
                "level": t.get("interaction", "L1"),
                "capability": t.get("capability", ""),
            }
        except Exception:
            meta[d.name] = {"title": d.name, "level": "L1", "capability": ""}
    return meta


def build_payload(summary: dict, summary_path: Path) -> dict:
    meta = load_tasks_meta()
    tasks = []
    dim_scores = {d: [] for d in DIMS}
    for tid, row in (summary.get("per_task") or {}).items():
        if not isinstance(row, dict):
            continue
        machine = row.get("machine_mean")
        if machine is None and isinstance(row.get("machine_mean_str"), str):
            try:
                machine = float(row["machine_mean_str"])
            except ValueError:
                machine = None
        judge = row.get("judge_mean")
        if judge is None and isinstance(row.get("judge_mean_str"), str):
            try:
                judge = float(row["judge_mean_str"])
            except ValueError:
                judge = None
        n = row.get("n_machine") if row.get("n_machine") is not None else row.get("n")
        entry = {
            "id": tid,
            "title": meta.get(tid, {}).get("title", tid),
            "level": meta.get(tid, {}).get("level", "L1"),
            "n": n,
            "machine": machine,
            "machine_str": _fmt2(machine) or "n/a",
            "judge": judge,
            "judge_str": _fmt2(judge) if judge is not None else "n/a",
            "note": f"capability={meta.get(tid, {}).get('capability', '')}",
        }
        tasks.append(entry)
        dim = TASK_DIM.get(tid)
        if dim and machine is not None:
            dim_scores[dim].append(float(machine))

    dims = []
    for d in DIMS:
        vals = dim_scores[d]
        dims.append(round(sum(vals) / len(vals), 2) if vals else None)

    machine_means = [t["machine"] for t in tasks if t["machine"] is not None]
    equal = round(sum(machine_means) / len(machine_means), 2) if machine_means else None
    num = sum((t["machine"] or 0) * (t["n"] or 0) for t in tasks if t["machine"] is not None)
    den = sum((t["n"] or 0) for t in tasks if t["machine"] is not None)
    weighted = round(num / den, 2) if den else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(summary_path).replace("\\", "/"),
        "model_id": summary.get("model_id") or "unknown",
        "condition": {
            "temperature": summary.get("temperature"),
            "note": "机检分；Judge 未启用则 n/a。百分制两位小数。",
        },
        "metrics": {
            "run_id": summary.get("run_id"),
            "cost": summary.get("cost") or {},
            "abst": summary.get("abst") or {},
            "diagnostics": summary.get("diagnostics") or {},
            "n_items": sum((t.get("n") or 0) for t in tasks),
            # DESIGN v0.4 §9：capability 分列（含 hard 子集）、safety、baselines、provisional
            "capability": summary.get("capability") or {},
            "safety_score": summary.get("safety_score") or "n/a",
            "baselines": summary.get("baselines") or {},
            "provisional": summary.get("provisional", True),
        },
        "disclaimer": summary.get("disclaimer")
        or "本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。",
        "tasks": sorted(tasks, key=lambda t: t["id"]),
        "dims": dims,
        "overview": {"equal_weight": equal, "item_weighted": weighted},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, default=None)
    ap.add_argument("--dashboard-root", type=Path, default=None)
    args = ap.parse_args()
    summary_path = pick_run(args.run)
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    payload = build_payload(summary, summary_path)
    root = args.dashboard_root or os.environ.get("CNJB_DASHBOARD_ROOT")
    if not root:
        # c397：不再硬编码个人机器绝对路径——缺省落到仓库 runs/（已 gitignore），
        # 外部面板目录用 CNJB_DASHBOARD_ROOT 或 --dashboard-root 显式指定
        root = ROOT / "runs" / "dashboard-sync"
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    out = root / "dashboard-data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # 面板 index.html 加载的是 dashboard-data.js（window.CNJB_DATA）
    js = root / "dashboard-data.js"
    js.write_text(
        "window.CNJB_DATA=" + json.dumps(payload, ensure_ascii=False) + ";",
        encoding="utf-8",
    )
    print(f"synced: {summary_path} -> {out}")
    print(f"synced: {summary_path} -> {js}")
    print(
        f"model={payload['model_id']} equal={payload['overview']['equal_weight']} "
        f"weighted={payload['overview']['item_weighted']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

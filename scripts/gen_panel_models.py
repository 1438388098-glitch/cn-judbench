"""公开面板 MODELS 数据块再生器（c398）：summary.json 供数，ledger §1 供身份。

app.js 的 MODELS 块（MODELS:BEGIN/END 标记之间）不再手工维护：
- 总分/加权/难题分/CI/safety/八包分包 ← 各 run 的 ``*-scored/summary.json``；
- run 目录名/官方名/思考强度/成色 ← ``docs/run-score-ledger.md`` §1 主记分板
  （ledger 是唯一汇总账，身份字段属账面信息而非产物字段）。

用法::

    python scripts/gen_panel_models.py --check        # 只校验：再生块 == app.js 现块
    python scripts/gen_panel_models.py                # 就地再生 app.js MODELS 块

配套机检 tests/test_narrative_v06.py::test_c398（--check 模式）保证手改必被打回。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 分包列序 = app.js PACKAGES 顺序（法条时效→定罪→合同→长案→说理→抽取→费用期限→计算）
TASK_ORDER = [
    "cit_validity", "s_charge_subsume", "contract_risk", "long_horizon_case",
    "a_irac_reason", "u_element_extract", "gaia_fee_deadline", "calc_fail_to_pass",
]

LEDGER_ROW = re.compile(
    r"^\| \d+ \| `([a-z0-9\-]+)` \| ([^|]+?)（([^（）（）]+)） \| "
    r"(洁净隔离|API 隔离) \| \*{0,2}(\d+\.\d{2})\*{0,2} \|", re.M)


def load_ledger_meta(ledger_path: Path) -> dict[str, dict]:
    """§1 主记分板 → run → {name, think, purity}（按账面行序）。"""
    meta: dict[str, dict] = {}
    text = ledger_path.read_text(encoding="utf-8")
    body = text.split("## 1. 主记分板", 1)[1].split("## 2.", 1)[0]
    for m in LEDGER_ROW.finditer(body):
        run, name, think, purity, _grand = m.groups()
        meta[run] = {"name": name.strip(), "think": think.strip(), "purity": purity}
    return meta


def load_summary(run_dir: Path) -> dict | None:
    p = run_dir / "summary.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def render_entry(run: str, meta: dict, s: dict) -> str:
    cap = s["capability"]
    ci = cap.get("hard_ci95")
    ci_txt = f"[{float(ci[0]):.2f}, {float(ci[1]):.2f}]" if ci else "null"
    pt = s["per_task"]
    packages = [float(pt[t]["machine_mean_str"]) for t in TASK_ORDER]
    lines = [
        "  {",
        f'    run: "{run}",',
        f'    name: "{meta["name"]}",',
        f'    think: "{meta["think"]}",',
        f'    purity: "{meta["purity"]}",',
        f'    grand_eq: {float(cap["grand_eq"]):.2f},',
        f'    grand_w: {float(cap["grand_w"]):.2f},',
        f'    hard: {float(cap["hard"]):.2f},',
        f'    hard_ci: {ci_txt},',
        f'    safety: {float(s["safety_score"]):.2f},',
        f'    packages: [{", ".join(f"{v:.2f}" for v in packages)}],',
        "  },",
    ]
    return "\n".join(lines)


def render_block(runs_root: Path, ledger_path: Path) -> str:
    meta = load_ledger_meta(ledger_path)
    if not meta:
        raise SystemExit("ledger §1 主记分板解析为空（格式漂移？）")
    entries = []
    missing = []
    for run, m in meta.items():
        s = load_summary(runs_root / run)
        if s is None:
            missing.append(run)
            continue
        entries.append(render_entry(run, m, s))
    if missing:
        raise SystemExit(f"以下 run 缺 summary.json（reports/runs 为本地产，需在原机器再生）: {missing}")
    return "/* MODELS:BEGIN 由 scripts/gen_panel_models.py 生成；手改会被 c398 再生对齐机检打回 */\nconst MODELS = [\n" \
        + "\n".join(entries) + "\n];\n/* MODELS:END */"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-root", type=Path, default=ROOT / "reports" / "runs")
    ap.add_argument("--ledger", type=Path, default=ROOT / "docs" / "run-score-ledger.md")
    ap.add_argument("--app", type=Path, default=ROOT / "app.js")
    ap.add_argument("--check", action="store_true", help="只校验不写回")
    args = ap.parse_args()
    block = render_block(args.runs_root, args.ledger)
    app = args.app.read_text(encoding="utf-8")
    begin = app.find("/* MODELS:BEGIN")
    end = app.find("/* MODELS:END */")
    if begin == -1 or end == -1:
        raise SystemExit("app.js 缺 MODELS:BEGIN/END 标记")
    if app[begin:end + len("/* MODELS:END */")] == block:
        print("panel MODELS block: up-to-date")
        return 0
    if args.check:
        raise SystemExit("app.js MODELS 块与再生结果不一致——请跑 gen_panel_models.py 再生或核对账面")
    args.app.write_text(app[:begin] + block + app[end + len("/* MODELS:END */"):],
                        encoding="utf-8")
    print(f"panel MODELS block regenerated -> {args.app}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

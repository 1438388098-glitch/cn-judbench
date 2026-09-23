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


def _capability_by_id() -> dict[str, str]:
    import sys
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.capabilities import parse_capability
    out: dict[str, str] = {}
    for f in (REPO / "data" / "public").glob("*.jsonl"):
        for ln in f.read_text(encoding="utf-8-sig").splitlines():
            if ln.strip():
                d = json.loads(ln)
                if d.get("capability"):
                    out[d["id"]] = parse_capability(d["capability"])[0]
    return out


def _spearman(xs: list[float], ys: list[float]) -> float:
    """秩相关（平均秩处理并列，无 scipy 依赖）。"""
    def _ranks(vs):
        order = sorted(range(len(vs)), key=lambda i: vs[i])
        ranks = [0.0] * len(vs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vs[order[j + 1]] == vs[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[order[k]] = avg
            i = j + 1
        return ranks
    rx, ry = _ranks(xs), _ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy) if vx and vy else 0.0


def _author_difficulty_by_id() -> dict[str, int]:
    out: dict[str, int] = {}
    for f in (REPO / "data" / "public").glob("*.jsonl"):
        for ln in f.read_text(encoding="utf-8-sig").splitlines():
            if ln.strip():
                d = json.loads(ln)
                if d.get("difficulty") is not None:
                    out[d["id"]] = int(d["difficulty"])
    return out


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
        {"models": model_names, "rule": "p>=0.85:1; >=0.6:2; >=0.3:3; else 4",
         "models_note": "v05new-s1m/s2m 为同底座模型的两名隔离考生实例（E17），"
                        "p 是考生通过率而非跨模型通过率",
         "items": result},
        ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter
    hist = Counter(v["difficulty_emp"] for v in result.values())
    print(f"标定 {len(result)} 题 ← {len(model_names)} 模型: {model_names}")
    print("difficulty_emp 直方图:", dict(sorted(hist.items())))
    for iid, v in result.items():
        if v["difficulty_emp"] >= 3:
            print(f"  hard {iid}: p={v['p']:.2f} → d{v['difficulty_emp']}")

    # c171：作者难度 × 实证难度交叉表（C4 写作直接引用；4=最难）
    author = _author_difficulty_by_id()
    cross: dict[int, Counter] = {}
    for iid, v in result.items():
        if iid in author:
            cross.setdefault(author[iid], Counter())[v["difficulty_emp"]] += 1
    agree = sum(cnt[d] for d, cnt in cross.items())  # 对角线：作者档=实证档
    n_both = sum(sum(cnt.values()) for cnt in cross.values())
    # c233：作者难度 vs 实证通过率的 Spearman 秩相关（预期为负：越标难 p 越低）
    rho = _spearman([float(author[i]) for i in result if i in author],
                    [result[i]["p"] for i in result if i in author])
    # c234：能力维（主维）× 平均通过率——「哪一维最难」论文素材
    caps = _capability_by_id()
    by_cap: dict[str, list[float]] = {}
    for iid, v in result.items():
        if iid in caps:
            by_cap.setdefault(caps[iid], []).append(v["p"])
    cap_stat = {c: (len(ps), sum(ps) / len(ps)) for c, ps in sorted(by_cap.items())}
    md = [REPO / "reports" / "difficulty-emp-crosstab.md"]
    lines = [
        "# 作者难度 × 实证难度交叉表（c171 首跑）",
        "",
        f"- 标定源：{', '.join(model_names)}（同底座两隔离考生，E17；p 为考生通过率）",
        f"- 规则：{_band.__doc__ or 'p>=0.85→1; >=0.6→2; >=0.3→3; else→4'}（score≥60 计通过）",
        f"- 交叉 {n_both} 题（作者标注与实证标定双全者）；对角一致 {agree} 题"
        f"（{100 * agree / n_both if n_both else 0:.1f}%）",
        "",
        "| 作者难度 \\ 实证 | " + " | ".join(f"d{d}" for d in (1, 2, 3, 4)) + " |",
        "|---|" + "---|" * 4,
    ]
    for d in (1, 2, 3, 4):
        cnt = cross.get(d, Counter())
        lines.append(f"| d{d}（{sum(cnt.values())} 题） | "
                     + " | ".join(str(cnt.get(e, 0)) for e in (1, 2, 3, 4)) + " |")
    import sys
    sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.capabilities import CANONICAL_DIMS, CROSSCUTTING
    _labels = {**CANONICAL_DIMS, **CROSSCUTTING}
    lines += ["",
              f"- **Spearman（作者难度, 实证通过率）ρ = {rho:.3f}**（n={n_both}）——"
              "解读注意：ρ 接近 0 或为正即作者难度对实证难度几乎无预测力"
              "（与交叉表「作者 d4 的考生全对题」互证）；显著负值才是标注有效。",
              "",
              "## 能力维 × 实证通过率（c234，主维计数）",
              "",
              "| 维 | n | 平均通过率 |",
              "|---|---|---|"]
    for c, (n_c, mean_p) in cap_stat.items():
        lines.append(f"| {c}（{_labels.get(c, c)}） | {n_c} | {100 * mean_p:.2f}% |")
    # c306：退场候选（expansion-plan §4：作者标难 d≥3 而实证 p≥0.80 → 饱和嫌疑）
    exits = sorted(
        ((iid, v) for iid, v in result.items()
         if author.get(iid, 0) >= 3 and v["p"] >= 0.80),
        key=lambda x: x[0])
    lines += ["",
              f"## 退场候选（c306：作者 d≥3 且实证 p≥80%；共 {len(exits)} 题）",
              "",
              "> 处置按 docs/expansion-plan.md §4：改造加 hard 变体或移入 archive，",
              "> 不改 item_id、不重排行号；本清单仅基于本地考生 run（p 为考生通过率）。"]
    if exits:
        lines += [f"- {iid}（作者 d{author[iid]}，p={v['p']:.2f}）" for iid, v in exits]
    else:
        lines.append("- 无")
    lines += ["",
              "注：difficulty_emp 回写 jsonl 延后至 Sprint B 数据冻结（避免中途漂移 hash）；"
              "本表仅作论文「作者标注 vs 实证通过率」一致性分析素材。"]
    md[0].write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written: {md[0]}")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

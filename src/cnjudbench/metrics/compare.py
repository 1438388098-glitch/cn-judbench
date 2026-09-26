"""模型间配对比较（FRAMEWORK §8 统计口径；论文主表"A 比 B"的依据）。

- 分差配对 bootstrap 95% CI：复用 bootstrap.paired_bootstrap_ci（单一分位数口径）；
- McNemar 精确检验：通过/未通过位级配对（阈值口径与 report.csv solve% 一致），
  双侧精确二项 p（无 scipy 依赖，math.comb 精确整数组合数）。

输入是两个 run 目录的 summary.json（逐题分来自 tasks.*.items[].score）；
n/a 题不进配对样本，两侧缺失计数单列（比较只对齐两侧都有分的题）。
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path

from .bootstrap import paired_bootstrap_ci

SOLVE_THRESHOLD_DEFAULT = 60.0  # 与 report.csv solve% 同一口径

# 预注册比较单元（FRAMEWORK §8.3）：核心六包等权 grand——合计 168 题，
# capability 可比较 161 题（s_charge 7 道 safety 夹具被 role 过滤排除）。
# 事后挑比较子集是排名作弊的主要通道——凡用于排名主张的 A-B 比较，
# 必须同时给出本口径（--preregistered）。
CORE_SIX_TASKS = frozenset({
    "cit_validity", "u_element_extract", "s_charge_subsume",
    "contract_risk", "a_irac_reason", "long_horizon_case",
})

# 排名资格两档阈值（FRAMEWORK §8.3 文字与代码的唯一对齐点，测试锁定）
RANKABLE_MIN_N = 100
CI_DESCRIPTIVE_MIN_N = 50


def mcnemar_exact(a_pass: list[bool], b_pass: list[bool]) -> dict:
    """位级通过/未通过的 McNemar 精确检验（只看不一致对）。

    返回 n_discordant（01+10）、n_01（a错b对）、n_10（a对b错）、双侧精确 p。
    """
    if len(a_pass) != len(b_pass):
        raise ValueError("配对样本必须等长")
    n01 = sum(1 for x, y in zip(a_pass, b_pass) if not x and y)
    n10 = sum(1 for x, y in zip(a_pass, b_pass) if x and not y)
    n = n01 + n10
    if n == 0:
        return {"n_discordant": 0, "n_01": 0, "n_10": 0, "p_exact": 1.0}
    k = min(n01, n10)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)
    p = min(1.0, 2.0 * tail)
    return {"n_discordant": n, "n_01": n01, "n_10": n10, "p_exact": p}


def _item_scores(summary_path: Path) -> tuple[dict[str, float], dict[str, str], dict[str, str]]:
    """读 summary.json → ({item_id: score}, {item_id: role}, {item_id: task_id})；n/a 剔除。"""
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    scores: dict[str, float] = {}
    roles: dict[str, str] = {}
    tasks: dict[str, str] = {}
    for task_id, task in summary.get("tasks", {}).items():
        for it in task.get("items", []):
            if it.get("score") in (None, "n/a"):
                continue
            scores[it["id"]] = float(it["score"])
            roles[it["id"]] = it.get("role", "capability")
            tasks[it["id"]] = task_id
    return scores, roles, tasks


def _macro_paired_bootstrap(
    task_of: list[str], a: list[float], b: list[float], *, n_boot: int, seed: int
) -> dict:
    """包等权 macro 分差的配对 bootstrap（c144，FRAMEWORK §8.3 预注册口径）。

    层内重采样题目 → 各包均值 → 六包等权平均；分位数取法与
    bootstrap.paired_bootstrap_ci 一致（int(0.025*(n_boot-1))）。
    """
    by_task: dict[str, list[int]] = defaultdict(list)
    for idx, tid in enumerate(task_of):
        by_task[tid].append(idx)
    n_tasks = len(by_task)
    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(n_boot):
        ma = mb = 0.0
        for idxs in by_task.values():
            take = [idxs[rng.randrange(len(idxs))] for _ in idxs]
            ma += sum(a[i] for i in take) / len(take)
            mb += sum(b[i] for i in take) / len(take)
        deltas.append((ma - mb) / n_tasks)
    deltas.sort()
    point = (sum(a) - sum(b)) / len(a) if n_tasks == 0 else (
        sum(sum(a[i] for i in idxs) / len(idxs) for idxs in by_task.values())
        - sum(sum(b[i] for i in idxs) / len(idxs) for idxs in by_task.values())
    ) / n_tasks
    return {"point": point, "ci95_low": deltas[int(0.025 * (n_boot - 1))],
            "ci95_high": deltas[int(0.975 * (n_boot - 1))],
            "n_tasks": n_tasks, "seed": seed, "n_boot": n_boot}


def _eligibility(n_aligned: int, protocol: str = "FRAMEWORK §8.3") -> dict:
    """排名资格两档制（c326，FRAMEWORK §8.3）：n≥RANKABLE_MIN_N rankable；
    n≥CI_DESCRIPTIVE_MIN_N CI 仅 descriptive；再低 descriptive_only——
    CLI 据此抑制显著性结论措辞。"""
    if n_aligned >= RANKABLE_MIN_N:
        tier = "rankable"
    elif n_aligned >= CI_DESCRIPTIVE_MIN_N:
        tier = "ci_descriptive"
    else:
        tier = "descriptive_only"
    return {"tier": tier, "n_threshold": RANKABLE_MIN_N, "protocol": protocol}


def _is_provisional(run_dir: Path) -> bool:
    """run 是否 provisional（c429）：缺 manifest / manifest 不可解析 /
    provisional 标志为真，一律按 provisional 计——fail-closed。

    DESIGN v0.4 §8：provisional 产物不得进对外对比表；compare 是统计出口，
    不得让未过 flip 门禁/依赖锁定的 run 产出「显著」级结论。
    """
    mp = Path(run_dir) / "manifest.json"
    if not mp.is_file():
        return True
    try:
        return bool(json.loads(mp.read_text(encoding="utf-8")).get("provisional"))
    except (OSError, ValueError):
        return True


def compare_runs(
    run_a: Path,
    run_b: Path,
    *,
    threshold: float = SOLVE_THRESHOLD_DEFAULT,
    n_boot: int = 1000,
    seed: int = 42,
    preregistered: bool = False,
) -> dict:
    """两个 run 的同题配对比较：分差 CI + McNemar（capability 题）。

    preregistered=True 时只比核心六包（CORE_SIX_TASKS，FRAMEWORK §8.3
    预注册单元）；输出带 preregistered 标记与被剔除题数，供论文口径审计。
    """
    # c368：threshold 是百分制通过线（与 report.csv solve% 同口径），越界
    # 会静默产出全对/全错的 McNemar 位与显著性结论——c343 同纪律
    if not (0.0 <= threshold <= 100.0):
        raise ValueError(f"threshold={threshold} 越界：须在 [0,100]（百分制题分）")
    scores_a, roles_a, tasks_a = _item_scores(Path(run_a) / "summary.json")
    scores_b, roles_b, tasks_b = _item_scores(Path(run_b) / "summary.json")
    common_all = [i for i in scores_a if i in scores_b
                  and roles_a.get(i) == "capability" and roles_b.get(i) == "capability"]
    n_dropped = 0
    if preregistered:
        common = [i for i in common_all
                  if tasks_a.get(i) in CORE_SIX_TASKS and tasks_b.get(i) in CORE_SIX_TASKS]
        n_dropped = len(common_all) - len(common)
    else:
        common = common_all
    a = [scores_a[i] for i in common]
    b = [scores_b[i] for i in common]
    out: dict = {
        "run_a": str(run_a), "run_b": str(run_b), "threshold": threshold,
        "n_aligned": len(common),
        "n_only_a": sum(1 for i in scores_a if i not in scores_b),
        "n_only_b": sum(1 for i in scores_b if i not in scores_a),
        "preregistered": preregistered,
        "n_dropped_by_filter": n_dropped,
        # 逐题 diff（c137）：id/task/双侧分/通过位，供 --items-out 出附录表
        "items": [
            {"id": i, "task": tasks_a.get(i), "score_a": scores_a[i],
             "score_b": scores_b[i], "diff": scores_a[i] - scores_b[i],
             "a_pass": scores_a[i] >= threshold, "b_pass": scores_b[i] >= threshold}
            for i in common
        ],
    }
    if not common:
        out["error"] = "无共同 capability 题分，无法配对"
        return out
    out["mean_a"] = sum(a) / len(a)
    out["mean_b"] = sum(b) / len(b)
    out["paired_ci"] = paired_bootstrap_ci(a, b, n_boot=n_boot, seed=seed)
    out["mcnemar"] = mcnemar_exact([x >= threshold for x in a],
                                   [x >= threshold for x in b])
    # c326：排名资格两档制（FRAMEWORK §8.3）——小样本不再与 n≥100 同措辞
    out["eligibility"] = _eligibility(len(common))
    # c429：provisional 出口强制降档——任一侧 provisional（含缺 manifest）
    # 时不得产出 rankable/ci_descriptive 级结论，数字仅作描述性呈现
    prov_sides = sorted(name for name, run in (("run_a", run_a), ("run_b", run_b))
                        if _is_provisional(run))
    if prov_sides:
        out["eligibility"]["tier"] = "descriptive_only"
        out["eligibility"]["provisional_runs"] = prov_sides
        out["eligibility"]["downgraded_reason"] = (
            f"provisional run（{', '.join(prov_sides)}）未过 flip 门禁/依赖锁定，"
            "按 DESIGN §8 不得进对外对比表")
    if preregistered:
        # c144：六包等权 macro（FRAMEWORK §8.3「核心六包等权 grand」的题级实现）
        task_of = [tasks_a[i] for i in common]
        macro = _macro_paired_bootstrap(task_of, a, b, n_boot=n_boot, seed=seed)
        # c328：核心六包缺包 = 预注册单元被无声替换，必须显式告警
        missing = sorted(CORE_SIX_TASKS - set(task_of))
        macro["missing_tasks"] = missing
        if missing:
            macro["warning"] = (
                f"核心六包缺 {len(missing)} 包（{', '.join(missing)}），"
                "macro 实为"
                f"{len(set(task_of))} 包等权——不可与完整六包口径比较")
        out["macro_ci"] = macro
    return out

"""题库抽样规则（用户：跑测试时按规则抽取，不写死全量题数）。

规则（确定性、可复现）：
1. **分层**：按 task_id 分层；层内按 domain 二级分层。
2. **每层至少 1 题、至多 k 题**（默认 k=3），层内按 id 字典序取前 k（稳定）。
3. **必含夹具**：`t-fake-001`、含 `expect=refuse` 的题、含 dual as_of 的题（g-06）强制入样。
4. mock 全分检查对**抽样子集**断言，不对全库写死 n。

被 tests/ 共用，禁止在测试里硬编码题量等式。
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from cnjudbench.validate.items import load_items_file

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_K = 3
FORCE_IDS = ("t-fake-001", "g-06", "a-008", "tj-006")


def load_all_items(items_root: Path | None = None) -> list[Any]:
    root = items_root or (ROOT / "data" / "public")
    out: list[Any] = []
    for p in sorted(root.glob("*.jsonl")):
        out.extend(it for _ln, it in load_items_file(p))
    return out


def sample_items(
    items: Iterable[Any] | None = None, k: int = DEFAULT_K, *,
    prefer_unsaturated: bool = False,
) -> list[Any]:
    """分层抽样：task × domain，层内 id 序取前 k；强制夹具并入。

    prefer_unsaturated=True（c136）：层内排序键改为 (saturation_flag, id)——
    未饱和题优先入样。用途：区分度敏感的抽样评测（mock 门禁与测试用缺省
    False 保持既有行为不变；68 题饱和标注见 docs/dataset-card.md §1.1）。
    """
    items = list(items) if items is not None else load_all_items()
    by_id = {it.id: it for it in items}
    strata: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for it in items:
        strata[(it.task_id, getattr(it, "domain", "") or "")].append(it)
    picked: dict[str, Any] = {}
    for key in sorted(strata):
        order = ((lambda x: (bool(getattr(x, "saturation_flag", False)), x.id))
                 if prefer_unsaturated else (lambda x: x.id))
        for it in sorted(strata[key], key=order)[: max(1, k)]:
            picked[it.id] = it
    for fid in FORCE_IDS:
        if fid in by_id:
            picked[fid] = by_id[fid]
    return [picked[i] for i in sorted(picked)]


def coverage_report(items: Iterable[Any] | None = None) -> dict[str, set]:
    items = list(items) if items is not None else load_all_items()
    grid: dict[str, set] = defaultdict(set)
    for it in items:
        grid[it.task_id].add(getattr(it, "domain", "") or "?")
    return dict(grid)


def saturation_counts(items: Iterable[Any] | None = None) -> dict[str, int]:
    """各包饱和题（saturation_flag=true）计数（c136）：抽样与报告的区分度口径。"""
    items = list(items) if items is not None else load_all_items()
    out: dict[str, int] = defaultdict(int)
    for it in items:
        if getattr(it, "saturation_flag", False):
            out[it.task_id] += 1
    return dict(out)


if __name__ == "__main__":
    s = sample_items()
    print("sample_n", len(s), "of", len(load_all_items()))
    print("ids", [x.id for x in s])
    print("grid", {k: sorted(v) for k, v in coverage_report().items()})

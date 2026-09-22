"""holdout 隔离守卫（impl-P1.md §8 / impl-P1-rest §3 规则 4）。

holdout 永不入 git、永不进 prompt：run/run-all 的任何输入路径含 ``holdout``
目录段，或题面 ``split=holdout`` → 拒读并退出码 ≠ 0。
"""

from __future__ import annotations

from pathlib import Path


class HoldoutPathError(Exception):
    """holdout 数据出现在评测输入中（拒读）。"""


def assert_no_holdout(*paths: Path | str | None) -> None:
    for p in paths:
        if p is None:
            continue
        parts = {part.lower() for part in Path(p).parts}
        if "holdout" in parts:
            raise HoldoutPathError(f"holdout 路径禁止进入评测输入: {p}")


def assert_items_not_holdout(items: list) -> None:
    """题面级二次校验：split=holdout 的题面不得经 run 链路进 prompt。"""
    bad = [it.id for it in items if getattr(it, "split", None) == "holdout"]
    if bad:
        raise HoldoutPathError(f"题面 split=holdout 禁止进入 run（{', '.join(bad)}）；holdout 仅限内部评测")

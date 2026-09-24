"""cit_validity 冒烟对照（impl-P0a §6/§8）。

P0a 边界：只做「gold 期望 status vs lawkb 解析实际 status」对照，
**不调用模型**；模型侧执行器属 P0b。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .lawkb.resolve import resolve_article, slice_union_hash
from .lawkb.store import LawkbStore
from .schemas.item import Item
from .validate.items import load_items_file


@dataclass
class SmokeRow:
    item_id: str
    law: str
    article: str
    as_of: str
    expect_status: str
    actual_status: str
    version_id: str | None
    ok: bool


@dataclass
class SmokeReport:
    rows: list[SmokeRow] = field(default_factory=list)
    slice_union_hash: str | None = None

    @property
    def all_match(self) -> bool:
        return bool(self.rows) and all(r.ok for r in self.rows)

    @property
    def distinct_statuses(self) -> set[str]:
        return {r.actual_status for r in self.rows}


def run_smoke(items_path: Path, store: LawkbStore) -> SmokeReport:
    report = SmokeReport()
    resolved_hashes: list[str] = []

    # c410：目录模式只消费 cit_validity 题（smoke 是 cit 专属契约），混合题库
    # 不再误报「gold 必须为非空数组」
    for path in [items_path] if items_path.is_file() else sorted(items_path.rglob("*.jsonl")):
        for _lineno, item in load_items_file(path):
            if items_path.is_dir() and item.task_id != "cit_validity":
                continue
            _run_item(item, store, report, resolved_hashes)

    if resolved_hashes:
        report.slice_union_hash = slice_union_hash(resolved_hashes)
    return report


def _run_item(item: Item, store: LawkbStore, report: SmokeReport, resolved_hashes: list[str]) -> None:
    if not isinstance(item.gold, list) or not item.gold:
        raise ValueError(f"{item.id}: gold 必须为非空数组（cit_validity 契约）")
    for g in item.gold:
        try:
            law = g["law"]
            article = str(g["article"])
            as_of_raw = str(g["as_of"])
            expect = str(g["expect_status"])
        except (KeyError, TypeError) as e:
            raise ValueError(f"{item.id}: gold 元素缺字段 {e}（需 law/article/as_of/expect_status）") from e
        result = resolve_article(law, article, date.fromisoformat(as_of_raw), store)
        report.rows.append(
            SmokeRow(
                item_id=item.id,
                law=law,
                article=article,
                as_of=as_of_raw,
                expect_status=expect,
                actual_status=result.status,
                version_id=result.version_id,
                ok=result.status == expect,
            )
        )
        if result.status == "ok" and result.text_hash:
            resolved_hashes.append(result.text_hash)


def format_report(report: SmokeReport) -> str:
    lines = [
        f"{'item':<10} {'law':<14} {'article':<10} {'as_of':<12} "
        f"{'expect':<22} {'actual':<22} verdict"
    ]
    for r in report.rows:
        lines.append(
            f"{r.item_id:<10} {r.law:<14} {r.article:<10} {r.as_of:<12} "
            f"{r.expect_status:<22} {r.actual_status:<22} {'OK' if r.ok else 'FAIL'}"
            + (f" -> {r.version_id}" if r.version_id else "")
        )
    lines.append(f"rows={len(report.rows)} distinct_statuses={sorted(report.distinct_statuses)}")
    if report.slice_union_hash:
        lines.append(f"slice_union_hash={report.slice_union_hash}")
    lines.append("ALL MATCH" if report.all_match else "MISMATCH FOUND")
    return "\n".join(lines)

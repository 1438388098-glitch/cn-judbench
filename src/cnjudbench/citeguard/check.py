"""CiteGuard 三检：存在 / 条号 / 时效（impl-P0b §4.2）。

- 存在失败（``unresolved_law`` / ``unknown_in_lawkb``）→ ``wrong_article``；
  其中 ``unknown_in_lawkb`` 为**未入库**，报告分列，**不记幻觉**；
- 时效失败（``wrong_vintage`` / ``not_yet_effective`` / ``not_effective_on_as_of``）
  → ``stale_statute``；
- ``ambiguous_versions`` → 库数据错误：调用方须拒判并报警（本模块返回
  ``ambiguous=True``，execute 侧转为 ItemError）。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..lawkb.resolve import resolve_article
from ..lawkb.store import LawkbStore
from .extract import Claim

AMBIGUOUS = "ambiguous_versions"

_TIMING_FAIL = {"wrong_vintage", "not_yet_effective", "not_effective_on_as_of"}
_EXIST_FAIL = {"unresolved_law", "unknown_in_lawkb"}


@dataclass
class CiteCheck:
    claim: Claim
    resolve_status: str
    version_id: str | None = None
    text_hash: str | None = None
    exists: bool = False
    article_match: bool = False
    timely: bool = False
    ambiguous: bool = False
    unknown_in_lawkb: bool = False  # 分列标记：未入库 ≠ 幻觉
    taxonomy: str | None = None
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.exists and self.article_match and self.timely


def check_claim(claim: Claim, store: LawkbStore, as_of: str | None = None) -> CiteCheck:
    """对单条 claim 做三检；``as_of`` 缺省回落到 claim 自带值。

    均无 as_of 时以库快照「今天」不可取（附录 D 禁止 store_version 冒充），
    直接记 exists 失败并注明。
    """
    effective_as_of = as_of or claim.as_of
    if not effective_as_of:
        return CiteCheck(
            claim=claim,
            resolve_status="missing_as_of",
            taxonomy="wrong_article",
            note="claim 与题面均未提供 as_of，拒判（禁止以库发行日冒充）",
        )

    from datetime import date

    result = resolve_article(claim.law_raw, claim.article_raw, date.fromisoformat(effective_as_of), store)
    ambiguous = result.status == AMBIGUOUS
    unknown = result.status == "unknown_in_lawkb"
    exists = result.status == "ok"
    timely = result.status == "ok"

    taxonomy = None
    note = ""
    if result.status in _EXIST_FAIL:
        taxonomy = "wrong_article"
        if unknown:
            note = "unknown_in_lawkb（未入库，分列报告，不记幻觉）"
    elif result.status in _TIMING_FAIL:
        taxonomy = "stale_statute"
    elif ambiguous:
        note = "lawkb 多版本同窗（数据错误），须拒判报警"

    return CiteCheck(
        claim=claim,
        resolve_status=result.status,
        version_id=result.version_id,
        text_hash=result.text_hash,
        exists=exists,
        article_match=exists,  # resolve 成功即条号已规范化命中（D.4 第 4 步）
        timely=timely,
        ambiguous=ambiguous,
        unknown_in_lawkb=unknown,
        taxonomy=taxonomy,
        note=note,
    )

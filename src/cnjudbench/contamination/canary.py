"""污染一级：canary / 题面指纹泄漏（FRAMEWORK §9.1）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ContaminationHit:
    item_id: str
    kind: str  # canary | fingerprint
    detail: str


def scan_output(item_id: str, output_text: str, *, canary: str | None = None,
                fingerprint: str | None = None) -> list[ContaminationHit]:
    """输出中出现 canary 或题面指纹 → 一级污染命中（降权/警报，不进主榜可选）。"""
    hits: list[ContaminationHit] = []
    text = output_text or ""
    if canary and canary in text:
        hits.append(ContaminationHit(item_id, "canary", canary))
    if fingerprint and len(fingerprint) >= 8 and fingerprint in text:
        hits.append(ContaminationHit(item_id, "fingerprint", fingerprint[:32]))
    return hits


def temporal_note(*, split: str, item_date: str | None, cutoff: str | None) -> str | None:
    """二级：live 且题面日期在 cutoff 之后 → 报告分列提示。"""
    if split != "live" or not item_date or not cutoff:
        return None
    if item_date > cutoff:
        return f"live_after_cutoff:{item_date}>{cutoff}"
    return None

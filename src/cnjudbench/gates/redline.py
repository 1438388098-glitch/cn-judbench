"""红线 gate（FRAMEWORK §3.1 / §8.1）。"""

from __future__ import annotations

from dataclasses import dataclass

from cnjudbench.scale import cap_at, gate_zero


@dataclass
class GateHit:
    gate_id: str
    on_fail: str
    taxonomy: str


def apply_gates(score: float, hits: list[GateHit]) -> tuple[float, list[str]]:
    tags = [h.taxonomy for h in hits]
    if any(h.on_fail == "zero" for h in hits):
        return gate_zero(), tags
    for h in hits:
        if h.on_fail == "cap_50":
            score = cap_at(score, 50.0)
    return score, tags


def detect_redlines(*, fabricated: bool = False, over_promise: bool = False,
                    cite_ok: bool = True, structure_broken: bool = False) -> list[GateHit]:
    hits: list[GateHit] = []
    if fabricated:
        hits.append(GateHit("no_fabricated_case", "zero", "fabricated_case"))
    if over_promise:
        hits.append(GateHit("no_over_promise", "zero", "over_promise"))
    if not cite_ok:
        hits.append(GateHit("cite_cap", "cap_50", "miss_retrieve"))
    if structure_broken:
        hits.append(GateHit("structure_keep", "cap_50", "structure_broken"))
    return hits

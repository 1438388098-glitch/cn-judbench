"""claim 抽取（impl-P0b §4.1）。

- ``structured``：读 ``citations[]`` / ``law_anchors[]``，或顶层 ``{law, article}``
  （cit_validity 式单引用判定）；
- ``extract``：若答案带引用列表则检，否则零 claim；
- ``gen``：**仅**解析答案中的 JSON 段（围栏或纯 JSON）里的引用列表；
  抽不到 → ``claim_extract_miss``（降级 P1 rubric gate），**不得**正则扫全文。

Claim 形状：``{law_raw, article_raw, as_of?, version_id?}``。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

CLAIM_SOURCES = ("citations", "law_anchors")


@dataclass
class Claim:
    law_raw: str
    article_raw: str
    as_of: str | None = None
    version_id: str | None = None


@dataclass
class ClaimExtraction:
    claims: list[Claim] = field(default_factory=list)
    status: str = "ok"  # ok | claim_extract_miss | answer_unparseable


def parse_answer_json(text: str) -> Any:
    """宽松 JSON 解析：容忍 ```json 围栏；失败抛 ValueError。"""
    s = text.strip()
    m = _FENCE_RE.search(s)
    if m:
        s = m.group(1).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        start, end = s.find("{"), s.rfind("}")
        if 0 <= start < end:
            return json.loads(s[start : end + 1])
        raise ValueError("答案不是可解析的 JSON") from None


def _claim_from_obj(obj: dict) -> Claim | None:
    law = obj.get("law") or obj.get("law_raw")
    article = obj.get("article") or obj.get("article_raw")
    if not law or not article:
        return None
    return Claim(
        law_raw=str(law),
        article_raw=str(article),
        as_of=str(obj["as_of"]) if obj.get("as_of") else None,
        version_id=str(obj["version_id"]) if obj.get("version_id") else None,
    )


def extract_claims(answer: Any, output_type: str, answer_text: str = "") -> ClaimExtraction:
    """按输出型抽取引用 claim（§4.1 策略表）。"""
    if answer is None:
        return ClaimExtraction(status="answer_unparseable")

    claims: list[Claim] = []
    if isinstance(answer, dict):
        for key in CLAIM_SOURCES:
            for obj in answer.get(key) or []:
                if isinstance(obj, dict) and (c := _claim_from_obj(obj)):
                    claims.append(c)
        # 顶层单引用（cit_validity 式）：{law, article, ...}
        if not claims and (c := _claim_from_obj(answer)):
            claims.append(c)
        # 顶层声称的 version_id 归入首条缺省 claim（防「引用对、版本编造」绕过）
        if claims and answer.get("version_id") and not claims[0].version_id:
            claims[0].version_id = str(answer["version_id"])
        return ClaimExtraction(claims=claims, status="ok" if claims else "claim_extract_miss")

    if output_type == "gen" and answer_text:
        # gen：只解析 JSON 段；抽不到不扫全文
        try:
            parsed = parse_answer_json(answer_text)
        except ValueError:
            return ClaimExtraction(status="claim_extract_miss")
        return extract_claims(parsed, "structured")

    return ClaimExtraction(status="claim_extract_miss")

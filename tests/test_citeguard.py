"""CiteGuard 单测：claim 抽取策略 + 三检（存在/条号/时效）+ ambiguous 拒判。"""

import hashlib
from pathlib import Path

import pytest

from cnjudbench.citeguard.check import check_claim
from cnjudbench.citeguard.extract import Claim, extract_claims, parse_answer_json
from cnjudbench.lawkb.store import LawkbStore


# ---------- claim 抽取（§4.1） ----------

def test_extract_structured_citations_list():
    ans = {"charge": "盗窃罪",
           "citations": [{"law": "刑法", "article": "264", "as_of": "2024-06-01"}]}
    ex = extract_claims(ans, "structured")
    assert ex.status == "ok"
    assert len(ex.claims) == 1
    assert ex.claims[0].law_raw == "刑法"
    assert ex.claims[0].as_of == "2024-06-01"


def test_extract_top_level_single_ref_and_version_merge():
    ans = {"law": "刑法", "article": "264", "as_of": "2024-06-01",
           "status": "ok", "version_id": "cl_264_2011"}
    ex = extract_claims(ans, "structured")
    assert ex.status == "ok" and ex.claims[0].version_id == "cl_264_2011"


def test_extract_top_level_version_id_merges_into_citation_claim():
    # 引用列表在 citations，version_id 在顶层 → 须合并进首条 claim（防编造绕过）
    ans = {"citations": [{"law": "刑法", "article": "264", "as_of": "2024-06-01"}],
           "version_id": "made_up"}
    ex = extract_claims(ans, "structured")
    assert ex.claims[0].version_id == "made_up"


def test_extract_gen_only_json_block_never_full_text():
    fenced = '结论如下：\n```json\n{"citations": [{"law": "刑法", "article": "264"}]}\n```'
    ex = extract_claims("见引用", "gen", fenced)
    assert ex.status == "ok" and len(ex.claims) == 1
    # 无 JSON 段 → 降级标记，不得正则扫全文（即使正文里出现「刑法第264条」）
    ex2 = extract_claims("依据刑法第264条之规定……", "gen", "依据刑法第264条之规定……")
    assert ex2.status == "claim_extract_miss" and ex2.claims == []


def test_extract_none_answer():
    assert extract_claims(None, "structured").status == "answer_unparseable"


def test_parse_answer_json_tolerates_fence():
    assert parse_answer_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_answer_json('前置说明 {"a": {"b": 2}} 后缀') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        parse_answer_json("完全不是 JSON")


# ---------- 三检（§4.2，真实 lawkb） ----------

def test_check_ok(store):
    chk = check_claim(Claim("刑法", "264", "2024-06-01"), store)
    assert chk.ok and chk.version_id == "cl_264_2011" and chk.taxonomy is None


def test_check_timing_fail_maps_stale_statute(store):
    # 291之二 2021-03-01 施行，声称 2020 → not_yet_effective → stale_statute
    chk = check_claim(Claim("刑法", "291之二", "2020-06-01"), store)
    assert not chk.timely
    assert chk.taxonomy == "stale_statute"
    # 253之一 2009-02-28 才增设，声称 2008 → not_yet_effective（同为时效失败）
    chk2 = check_claim(Claim("刑法", "253之一", "2008-01-01"), store)
    assert chk2.resolve_status == "not_yet_effective"
    assert chk2.taxonomy == "stale_statute"


def test_check_unknown_in_lawkb_not_hallucinated(store):
    chk = check_claim(Claim("刑法", "999", "2024-06-01"), store)
    assert chk.unknown_in_lawkb and not chk.exists
    assert chk.taxonomy == "wrong_article"  # 记 wrong_article，但明确分列
    assert "不记幻觉" in chk.note or "unknown" in chk.note


def test_check_unresolved_law(store):
    chk = check_claim(Claim("不存在的法典名", "1", "2024-06-01"), store)
    assert not chk.exists and chk.taxonomy == "wrong_article"


def test_check_missing_as_of_rejects(store):
    chk = check_claim(Claim("刑法", "264", None), store)
    assert not chk.exists
    assert "as_of" in chk.note  # 拒判：禁止以库发行日冒充


def test_check_ambiguous_requires_reject(tmp_path: Path):
    """两版本同窗 → ambiguous（库数据错误），调用方拒判报警。"""
    root = tmp_path / "lawkb"
    (root / "laws").mkdir(parents=True)
    (root / "text").mkdir()
    (root / "VERSION").write_text("lawkb-2026.09.1", encoding="utf-8")
    for vid, body in (("amb_v1", "甲本"), ("amb_v2", "乙本")):
        (root / "text" / f"{vid}.txt").write_text(body, encoding="utf-8")
    versions = []
    for vid in ("amb_v1", "amb_v2"):
        digest = "sha256:" + hashlib.sha256((root / "text" / f"{vid}.txt").read_bytes()).hexdigest()
        versions.append({
            "law_id": "amb_law", "article_no": "1", "version_id": vid,
            "effective_from": "2020-01-01", "effective_to": None,
            "superseded_by": None, "note": "", "text_hash": digest,
            "text_ref": f"text/{vid}.txt",
        })
    (root / "laws" / "amb.yaml").write_text(
        yaml_dump({"law": {"law_id": "amb_law", "names": ["重叠法"],
                          "level": "law", "promulgated_on": "2020-01-01"},
                   "article_version": versions}),
        encoding="utf-8",
    )
    store = LawkbStore.load(root)
    chk = check_claim(Claim("重叠法", "1", "2022-06-01"), store)
    assert chk.ambiguous
    assert not chk.ok
    assert "报警" in chk.note


def yaml_dump(obj) -> str:
    import yaml

    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False)

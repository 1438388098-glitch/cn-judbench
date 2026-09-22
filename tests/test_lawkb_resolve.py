"""lawkb 解析器单测：附录 D.3 归一化 + D.4 四态 + D.5 切片 hash。

全部用例基于 tmp 目录自建夹具，不依赖仓库内的真实条文表。
"""

import hashlib
from datetime import date
from pathlib import Path

import pytest
import yaml

from cnjudbench.lawkb.resolve import (
    lookup_law,
    normalize_article_no,
    normalize_law_name,
    resolve_article,
    slice_union_hash,
)
from cnjudbench.lawkb.store import LawkbError, LawkbStore


def write_store(tmp_path: Path, laws: list[dict], store_version: str = "lawkb-2026.09.1") -> Path:
    """按 spec 构建 lawkb 目录：laws=[{law: {...}, article_version: [{..., text}]}]。"""
    root = tmp_path / "lawkb"
    (root / "laws").mkdir(parents=True)
    (root / "text").mkdir()
    (root / "VERSION").write_text(store_version, encoding="utf-8")
    for i, lf in enumerate(laws):
        for v in lf["article_version"]:
            text = v.pop("text")
            (root / "text" / f"{v['version_id']}.txt").write_bytes(text.encode("utf-8"))
            v["text_ref"] = f"text/{v['version_id']}.txt"
            v["text_hash"] = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        (root / "laws" / f"law{i}.yaml").write_text(
            yaml.safe_dump(lf, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    return root


def law_spec(law_id: str = "test_law", names: list[str] | None = None) -> dict:
    return {
        "law": {
            "law_id": law_id,
            "names": names or ["测试法律", "《测试法律》"],
            "level": "law",
            "promulgated_on": "2000-01-01",
        },
        "article_version": [],
    }


def article(law_id: str, no: str, vid: str, eff_from: str, eff_to: str | None, text: str) -> dict:
    return {
        "law_id": law_id,
        "article_no": no,
        "version_id": vid,
        "text_hash": "",
        "effective_from": eff_from,
        "effective_to": eff_to,
        "superseded_by": None,
        "text_ref": "",
        "note": "",
        "text": text,
    }


# ---------- D.3 归一化 ----------


@pytest.mark.parametrize(
    "raw,expect",
    [
        ("第264条", "264"),
        ("２６４", "264"),
        (" 264 ", "264"),
        ("第205之一条", "205之一"),
        ("253之一", "253之一"),
    ],
)
def test_normalize_article_no(raw, expect):
    assert normalize_article_no(raw) == expect


@pytest.mark.parametrize(
    "raw,expect",
    [
        ("《中华人民共和国刑法》", "中华人民共和国刑法"),
        ("  刑法  ", "刑法"),
        ("《 合同法解释（二） 》", "合同法解释(二)"),
    ],
)
def test_normalize_law_name(raw, expect):
    assert normalize_law_name(raw) == expect


# ---------- D.4 四态 ----------


def test_ok_unique_version(tmp_path):
    lf = law_spec()
    lf["article_version"] = [article("test_law", "1", "t1_v1", "2000-01-01", None, "第一条文本")]
    store = LawkbStore.load(write_store(tmp_path, [lf]))
    r = resolve_article("测试法律", "第1条", date(2024, 6, 1), store)
    assert r.status == "ok"
    assert r.version_id == "t1_v1"
    assert r.text == "第一条文本"
    assert r.text_hash and r.text_hash.startswith("sha256:")


def test_version_slice_two_versions(tmp_path):
    lf = law_spec()
    lf["article_version"] = [
        article("test_law", "264", "old_v", "1997-10-01", "2011-05-01", "旧版"),
        article("test_law", "264", "new_v", "2011-05-01", None, "新版"),
    ]
    lf["article_version"][0]["superseded_by"] = "new_v"
    store = LawkbStore.load(write_store(tmp_path, [lf]))
    old = resolve_article("测试法律", "264", date(2010, 6, 1), store)
    new = resolve_article("测试法律", "264", date(2024, 6, 1), store)
    boundary = resolve_article("测试法律", "264", date(2011, 5, 1), store)
    assert (old.status, old.version_id) == ("ok", "old_v")
    assert (new.status, new.version_id) == ("ok", "new_v")
    assert (boundary.status, boundary.version_id) == ("ok", "new_v")  # 右开：失效日当天已归新版


def test_not_yet_effective(tmp_path):
    lf = law_spec()
    lf["article_version"] = [article("test_law", "2", "future_v", "2021-03-01", None, "未来条文")]
    store = LawkbStore.load(write_store(tmp_path, [lf]))
    r = resolve_article("测试法律", "2", date(2020, 6, 1), store)
    assert r.status == "not_yet_effective"
    assert r.version_id is None


def test_wrong_vintage(tmp_path):
    lf = law_spec()
    lf["article_version"] = [article("test_law", "3", "dead_v", "2009-05-13", "2021-01-01", "已废止")]
    store = LawkbStore.load(write_store(tmp_path, [lf]))
    r = resolve_article("测试法律", "3", date(2021, 6, 1), store)
    assert r.status == "wrong_vintage"


def test_ambiguous_versions_rejects(tmp_path):
    lf = law_spec()
    lf["article_version"] = [
        article("test_law", "4", "amb_v1", "2000-01-01", None, "A"),
        article("test_law", "4", "amb_v2", "2010-01-01", None, "B"),
    ]
    store = LawkbStore.load(write_store(tmp_path, [lf]))
    r = resolve_article("测试法律", "4", date(2024, 6, 1), store)
    assert r.status == "ambiguous_versions"
    assert r.version_id is None and r.text is None  # 拒判，不给任何文本


def test_unknown_in_lawkb(tmp_path):
    lf = law_spec()
    lf["article_version"] = [article("test_law", "1", "t1_v1", "2000-01-01", None, "第一条文本")]
    store = LawkbStore.load(write_store(tmp_path, [lf]))
    r = resolve_article("测试法律", "999", date(2024, 6, 1), store)
    assert r.status == "unknown_in_lawkb"


def test_unresolved_law_never_guesses(tmp_path):
    lf = law_spec()
    lf["article_version"] = [article("test_law", "1", "t1_v1", "2000-01-01", None, "第一条文本")]
    store = LawkbStore.load(write_store(tmp_path, [lf]))
    r = resolve_article("测试条例", "1", date(2024, 6, 1), store)
    assert r.status == "unresolved_law"
    n = lookup_law("《测试法律》", store)
    assert (n.status, n.law_id) == ("ok", "test_law")  # 书名号归一后精确命中


# ---------- 加载期完整性 ----------


def test_hash_mismatch_raises(tmp_path):
    lf = law_spec()
    lf["article_version"] = [article("test_law", "1", "t1_v1", "2000-01-01", None, "第一条文本")]
    root = write_store(tmp_path, [lf])
    bad = yaml.safe_load((root / "laws" / "law0.yaml").read_text(encoding="utf-8"))
    bad["article_version"][0]["text_hash"] = "sha256:" + "0" * 64
    (root / "laws" / "law0.yaml").write_text(
        yaml.safe_dump(bad, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(LawkbError, match="text_hash"):
        LawkbStore.load(root)


def test_duplicate_version_id_raises(tmp_path):
    a, b = law_spec(), law_spec("other_law")
    # 同 version_id 共享同一文本文件，文本必须一致才能到达重复检查（hash 先行）
    a["article_version"] = [article("test_law", "1", "dup_v", "2000-01-01", None, "A")]
    b["article_version"] = [article("other_law", "1", "dup_v", "2000-01-01", None, "A")]
    with pytest.raises(LawkbError, match="重复"):
        LawkbStore.load(write_store(tmp_path, [a, b]))


def test_missing_superseded_target_raises(tmp_path):
    lf = law_spec()
    v = article("test_law", "1", "t1_v1", "2000-01-01", None, "A")
    v["superseded_by"] = "ghost_v"
    lf["article_version"] = [v]
    with pytest.raises(LawkbError, match="superseded_by"):
        LawkbStore.load(write_store(tmp_path, [lf]))


def test_bad_store_version_raises(tmp_path):
    lf = law_spec()
    lf["article_version"] = [article("test_law", "1", "t1_v1", "2000-01-01", None, "A")]
    with pytest.raises(LawkbError, match="VERSION"):
        LawkbStore.load(write_store(tmp_path, [lf], store_version="v1"))


def test_alias_conflict_raises(tmp_path):
    a, b = law_spec("law_a", ["同名法"]), law_spec("law_b", ["同名法"])
    a["article_version"] = [article("law_a", "1", "va", "2000-01-01", None, "A")]
    b["article_version"] = [article("law_b", "1", "vb", "2000-01-01", None, "B")]
    with pytest.raises(LawkbError, match="别名冲突"):
        LawkbStore.load(write_store(tmp_path, [a, b]))


# ---------- D.5 切片 hash ----------


def test_slice_union_hash_stable_and_order_free():
    h1, h2, h3 = ("sha256:" + "a" * 64, "sha256:" + "b" * 64, "sha256:" + "c" * 64)
    a = slice_union_hash([h1, h2, h3])
    b = slice_union_hash([h3, h1, h2])
    assert a == b and a.startswith("sha256:")
    assert a != slice_union_hash([h1, h2])
    assert slice_union_hash([h1, h1]) != slice_union_hash([h1])  # 不去重：逐版本计入

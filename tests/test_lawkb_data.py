"""仓库内最小条文表的真实数据测试（附录 D.6 / impl-P0a §4.5）。"""

from datetime import date

from cnjudbench.lawkb.resolve import resolve_article


def test_min_table_scope(store):
    criminal = [v for v in store.versions.values() if v.law_id == "npc_criminal_law"]
    civil = [v for v in store.versions.values() if v.law_id == "npc_civil_code"]
    ji_laws = [m for m in store.laws.values() if m.level == "judicial_interpretation"]
    assert len(criminal) >= 8  # 刑法 ≥8 版本（含修正时点）
    assert len(civil) >= 4  # 民法典 ≥4 版本
    assert len(ji_laws) >= 2  # 司法解释 ≥2 件


def test_known_resolutions(store):
    ok_new = resolve_article("刑法", "264", date(2024, 6, 1), store)
    ok_old = resolve_article("刑法", "264", date(2010, 6, 1), store)
    assert (ok_new.status, ok_new.version_id) == ("ok", "cl_264_2011")
    assert (ok_old.status, ok_old.version_id) == ("ok", "cl_264_1997")
    assert ok_old.text_hash != ok_new.text_hash

    assert resolve_article("刑法", "291之二", date(2020, 6, 1), store).status == "not_yet_effective"
    assert resolve_article("民法典", "188", date(2020, 6, 1), store).status == "not_yet_effective"
    assert (
        resolve_article("合同法解释（二）", "26", date(2021, 6, 1), store).status == "wrong_vintage"
    )
    assert resolve_article("刑法", "400", date(2024, 6, 1), store).status == "unknown_in_lawkb"
    assert resolve_article("治安管理处罚条例", "19", date(2024, 6, 1), store).status == "unresolved_law"


def test_ji_multi_version(store):
    a = resolve_article("民间借贷司法解释", "25", date(2020, 9, 15), store)
    b = resolve_article("民间借贷司法解释", "25", date(2021, 6, 1), store)
    assert (a.status, a.version_id) == ("ok", "spc_pl_25_2020")
    assert (b.status, b.version_id) == ("ok", "spc_pl_25_2021")


def test_abolished_ji_has_abolished_on(store):
    meta = store.laws["spc_contract_interp_ii_2009"]
    assert meta.abolished_on is not None

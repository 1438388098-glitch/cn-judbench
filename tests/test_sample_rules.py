"""抽样规则金样：跑测试按 task×domain 分层抽取，不写死全库题量。"""

from __future__ import annotations

from cnjudbench.sample import coverage_report, sample_items


def test_sample_is_stratified_and_stable():
    s1 = sample_items()
    s2 = sample_items()
    assert [x.id for x in s1] == [x.id for x in s2]
    assert len(s1) >= 20
    assert {x.task_id for x in s1} >= {
        "cit_validity", "u_element_extract", "s_charge_subsume",
        "contract_risk", "a_irac_reason", "tool_search_statute",
        "gaia_fee_deadline", "tau_jud_intake", "long_horizon_case",
    }
    ids = {x.id for x in s1}
    assert "t-fake-001" in ids and "g-06" in ids


def test_coverage_grid_full_8_domains():
    grid = coverage_report()
    domains = {
        "civil_commercial", "criminal", "contract_compliance", "labor",
        "family", "ip", "administrative", "enforcement",
    }
    for task, doms in grid.items():
        missing = domains - doms
        assert not missing, f"{task} 缺科目: {missing}"

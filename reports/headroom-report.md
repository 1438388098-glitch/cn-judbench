# 扩题/削题余量报告（scripts/headroom_report.py 自动生成）

信号：饱和率 = saturation_flag 占比（作者侧头部全分标注）；rules = 无知识
策略得分；实证 p = 双考生通过率（仅有 run 数据的题）。余量判定：
饱和率≥30% 且实证 p≥60% → 低（优先新增该维度难题）；否则 ≥15% → 中；其余 → 高。

| 任务包 | n | 饱和率 | rules 基线 | 实证 p | 扩题余量 |
|---|---|---|---|---|---|
| a_irac_reason | 34 | 23.5% | 11.76 | 43.18% | 中 |
| calc_fail_to_pass | 54 | 55.6% | 79.63 | 100.00% | 低 |
| cit_validity | 27 | 0.0% | 66.67 | n/a | 高 |
| contract_risk | 23 | 0.0% | 0.00 | 25.00% | 高 |
| dms_side_effect_intake | 20 | 35.0% | 0.00 | 87.50% | 低 |
| gaia_fee_deadline | 23 | 0.0% | 17.39 | 91.67% | 高 |
| long_horizon_case | 15 | 0.0% | 0.00 | 8.33% | 高 |
| s_charge_subsume | 20 | 0.0% | 0.00 | n/a | 高 |
| tau_jud_intake | 16 | 0.0% | 0.00 | 0.00% | 高 |
| tool_fault_recovery | 16 | 0.0% | 0.00 | n/a | 高 |
| tool_search_statute | 26 | 0.0% | 0.00 | n/a | 高 |
| u_element_extract | 49 | 46.9% | 40.82 | 91.67% | 低 |

## 建议

- 余量低的包（calc_fail_to_pass, dms_side_effect_intake, u_element_extract）：新题注入其**未饱和维度**（capability 复合维或更高 interaction 级），或直接新建包；
- rules ≥60 的包（见 reports/baseline-report.md）：先修判分泄露面再扩题；
- 实证 p=100 的题族（difficulty-emp-crosstab.md d1 列）：候选削题或加 hard 变体。

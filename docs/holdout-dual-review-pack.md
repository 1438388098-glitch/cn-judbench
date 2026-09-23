# holdout 冻结双人复核材料包

> 生成日期：2026-09-24 · 抽样比例 30% · 种子前缀 `cnjb-holdout-v1:<task_id>`（sha256 前 8 hex，任何人可复算）

## 复核清单（每位复核人独立完成后签字）

1. 逐包核对入选题数 = max(3, ceil(n×0.30))，与下表一致；
2. 复算任选 2 包的种子与抽样序列（改动任一题的 id 集应可发现）；
3. 抽查 5 题确认 hard（difficulty≥3）保比例逻辑；
4. 确认 data/public 对应行删除后 `cnjudbench validate` 与 pytest 全绿；
5. 双人签字后，由执行人运行 `python scripts/freeze_holdout.py --apply` 并归档本文件。

| 任务包 | 包内题数 | 拟冻结 | hard 占比 |
|---|---|---|---|
| a_irac_reason | 34 | 11 (10/11 hard) | 32/34 |
| calc_fail_to_pass | 54 | 17 (13/17 hard) | 41/54 |
| cit_validity | 27 | 9 (4/9 hard) | 12/27 |
| contract_risk | 23 | 7 (4/7 hard) | 14/23 |
| dms_side_effect_intake | 20 | 6 (6/6 hard) | 19/20 |
| gaia_fee_deadline | 23 | 7 (6/7 hard) | 20/23 |
| long_horizon_case | 15 | 5 (5/5 hard) | 15/15 |
| s_charge_subsume | 20 | 6 (6/6 hard) | 19/20 |
| tau_jud_intake | 16 | 5 (3/5 hard) | 9/16 |
| tool_fault_recovery | 16 | 5 (5/5 hard) | 16/16 |
| tool_search_statute | 26 | 8 (2/8 hard) | 5/26 |
| u_element_extract | 49 | 15 (10/15 hard) | 34/49 |

**合计拟冻结 101 题。**

## 签字栏

- 复核人 A：____________ 日期：________
- 复核人 B：____________ 日期：________
- 执行人（--apply 后回填 commit/manifest）：____________

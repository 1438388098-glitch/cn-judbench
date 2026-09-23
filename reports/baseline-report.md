# 基线分布报告（D:\Claudeworkspace\cn-judbench\reports\runs\baseline-v06，阈值 ≥90 警告）

| 基线 | 任务包 | 分 |
|---|---|---|
| random | cit_validity | 45.93 |
| random | calc_fail_to_pass | 14.81 |
| random | a_irac_reason | 2.94 |
| random | u_element_extract | 0.00 |
| random | s_charge_subsume | 0.00 |
| random | contract_risk | 0.00 |
| random | long_horizon_case | 0.00 |
| random | gaia_fee_deadline | 0.00 |
| rules | calc_fail_to_pass | 79.63 |
| rules | cit_validity | 66.67 |
| rules | u_element_extract | 40.82 |
| rules | gaia_fee_deadline | 17.39 |
| rules | a_irac_reason | 11.76 |
| rules | s_charge_subsume | 0.00 |
| rules | contract_risk | 0.00 |
| rules | long_horizon_case | 0.00 |

## 警告（接近满分 = 判分可被无知识策略满足，须逐项归因）

- 无：全部基线分 < 90

归因口径（R7 c161）：rules 恒答 ok 对 expect=ok 题恒满是结构性非泄题；
random 单题满分是确定性词汇抽取运气。判分锚引用（law_anchors）
不得进基线可见面（R17）。

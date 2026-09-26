# gaia_fee_deadline（L3a 23 题）

FRAMEWORK §4.3 Exact oracle / impl-P2 §4。卷宗要素自包含于题面
（g-01..g-23：诉讼费/期间/条号/金额/时间线）；gold 终答不进 prompt，
`steps` 供模型外化关键步骤。

- 指标：resolve rate ×100（exact 主分，错即 0.00）+ progress（诊断列，不进主分）；
- 按题谓词分派：金额题 `predicates_fee.yaml`、日期题 `predicates_deadline.yaml`、
  文字题默认 `predicates.yaml`；三者共用 `progress_keyword` 诊断（读 gold.progress）；
- 双 as_of：g-06 同题对比民法典第188条在 2020-06-01 与 2021-06-01 的状态；
- 金样来源：`src/cnjudbench/tools/gold/fee.json` 同一费率实现 + lawkb `resolve_article` 施行日。

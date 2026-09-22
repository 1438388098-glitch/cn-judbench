# cit_validity

横切能力 **Cit（引用真伪/条号/时效）** 的冒烟任务包：给定法律引用与 `as_of`，
判断其在当日是否指向有效条文版本。

- **许可**：法条文本不受著作权保护；金样与题面随仓库（数据/代码许可分表见
  FRAMEWORK §10）。
- **污染风险**：`public`、`low`——题面为合成的引用核验探针，不含可背诵长文。
- **Verified 状态**：`draft`（P0a；进入 `active` 前需三人合议，FRAMEWORK §6）。
- **依赖**：lawkb 最小条文表（`lawkb/`，生成脚本 `scripts/build_min_lawkb.py`）。
  标注 `待校对` 的条文文本须人工核验后才能影响任何判分。

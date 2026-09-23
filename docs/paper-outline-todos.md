# 论文骨架待办清单（c210，2026-09-24 盘点）

> 来源：`docs/paper-outline.md` 中全部 ⬜ 槽位与待办段的集中清单，供写作期
> 逐项销账；每项后括号内为阻塞物。盘点时测试基线：421 绿 / CI 8 步。

## 数据槽位（进实验章表格）

- [ ] T1 主表：DS v0.4 复跑缺（DeepSeek 有效密钥；v0.6 基线表已备 baseline-v06，GLM v0.4 与 v0.6 基线已齐）
- [ ] T2 区分度：DS×GLM v0.4 重算（同上密钥阻塞）
- [ ] T6 人评：κ≥0.7 子样本（人评招募；协议与 kappa.py 已备）

## 待办段（§9 / §10）

- [ ] DS v0.4 全量复跑（密钥）→ T1/T2 补全；转存必须程序化（人工摘录致分数失真，见 calc-real-model-report.md §C）
- [ ] holdout 冻结执行（`freeze_holdout.py --apply` 待双人复核签字；未执行前正文不得声称双库）
- [ ] 人评 κ 试点（招募）
- [ ] lawkb 惰性锚补库（docs/lawkb-ingest-queue.md 16 键，准入=audit_anchors；零扣分不阻塞投稿正文）
- [ ] Live 滚动子集（协议文已备，执行排期未定）
- [ ] §9 其余 ⬜：以 paper-outline 原文为准逐条核对（本清单由 grep ⬜ 生成于 2026-09-24，条目 5 项）

## 已齐备（无需动作，防重复盘点）

- v0.6 基线表（baseline-v06：random 7.96 / rules 27.03 / gold 100×8）
- E18/E19 消融与复现数字（活体金样测试锁定：test_e18_repro_golden_v06 / test_passk_golden_v06）
- 作者×实证难度交叉表（difficulty-emp-crosstab.md：对角一致 33.9%）
- 能力维覆盖矩阵（capability-matrix.md：8+1 维全非零）
- 判分反刷分处置台账（research-notes-round3.md 45 条）

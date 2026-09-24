# 论文骨架待办清单（c210，2026-09-24 盘点）

> 来源：`docs/paper-outline.md` 中全部 ⬜ 槽位与待办段的集中清单，供写作期
> 逐项销账；每项后括号内为阻塞物。盘点时测试基线：421 绿 / CI 8 步
> （R30 复盘：569 绿 / CI 8 步 + 判效修复组 + 零漂移纪律 + E20 叙事齐备）。

## 数据槽位（进实验章表格）

- [x] T1 主表 DS 行：v0.6 全 12 包完成（ds-flash-v06-full/-tools，grand 68.72、flip 0%、$0.56）；T1 还差 GLM 工具轨 v0.6 重跑与 CI 列（能力 8 包 GLM 三档已入账：69.22/64.18/59.14）
- [ ] T2 区分度：DS×GLM v0.4 重算（同上密钥阻塞）
- [ ] T6 人评：κ≥0.7 子样本（人评招募；协议与 kappa.py 已备）

## 待办段（§9 / §10）

- [x] DS 全量复跑（2026-09-24 密钥恢复，API 直跑无转存问题）；T2 能力 8 包已对齐（DS 68.72 vs GLM 三档），工具轨对齐待 GLM v0.6 重跑
- [ ] holdout 冻结执行（`freeze_holdout.py --apply` 待双人复核签字；未执行前正文不得声称双库）
- [ ] 人评 κ 试点（招募）
- [ ] lawkb 惰性锚补库（docs/lawkb-ingest-queue.md 16 键，准入=audit_anchors；零扣分不阻塞投稿正文）
- [ ] Live 滚动子集（协议文已备，执行排期未定）
- [ ] §9 其余 ⬜：以 paper-outline 原文为准逐条核对（本清单由 grep ⬜ 生成于 2026-09-24，条目 5 项）

## 已齐备（无需动作，防重复盘点）

- v0.6 基线表（baseline-v06：random 7.96 / rules 27.03 / gold 100×8；修复后零漂移凭证 baseline-v06b）
- E18/E19 消融与复现数字（活体金样测试锁定：test_e18_repro_golden_v06 / test_passk_golden_v06）
- 作者×实证难度交叉表（difficulty-emp-crosstab.md：对角一致 33.9%）
- 能力维覆盖矩阵（capability-matrix.md：8+1 维全非零）
- 判分反刷分处置台账（research-notes-round3.md 45 条）
- 判分效度反自证审计（E20：c322-c324 修复 + baseline-v06b 零漂移 + FRAMEWORK §8.4 重导纪律）
- 时间效力轴判定面草稿（ct-201..211，11 窗探针验证；待真考生轮与 lawkb 补库）

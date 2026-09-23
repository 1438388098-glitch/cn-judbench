# docs 索引

CN-JudBench 全部文档的分组导航（c276）。新增 `docs/*.md` 时必须在本页登记
（`tests/test_calibration_release_v06.py` 机检全收录）。

## 框架与设计

| 文档 | 内容 |
|---|---|
| [../FRAMEWORK.md](../FRAMEWORK.md) | 评测框架总纲（维/包/计分/判分纪律） |
| [DESIGN-benchmark-optimization-v0.4.md](DESIGN-benchmark-optimization-v0.4.md) | v0.4 计分架构设计（role/hard 分层、provisional） |
| [DESIGN-difficulty-practice-v05.md](DESIGN-difficulty-practice-v05.md) | v0.5 难度分层与实务题设计 |

## 数据与题库

| 文档 | 内容 |
|---|---|
| [dataset-card.md](dataset-card.md) | 数据集卡（构成/口径/引用 BibTeX） |
| [difficulty-audit-v05.md](difficulty-audit-v05.md) | v0.5 难度审计 |
| [difficulty-emp-calc.md](difficulty-emp-calc.md) | calc 包实证难度 |
| [benchmark-discrimination-review.md](benchmark-discrimination-review.md) | 区分度评审（at/lh/c 双考生） |
| [u-hard-subset-report.md](u-hard-subset-report.md) | u 包难题子集 |
| [lawkb-fragment-fee-ms-xy.yaml](lawkb-fragment-fee-ms-xy.yaml) | lawkb 切片样例 |
| [lawkb-ingest-queue.md](lawkb-ingest-queue.md) | 法条文本入库队列（生成器产物） |
| [statute-sources.md](statute-sources.md) | 法条来源登记（官方数据库/最高法官网） |
| sources/ | 官方来源存档（HTML 原文） |
| corpus.txt | 参考语料（lawkb 文本聚合，README 示例引用） |

## 协议与政策（对外评审必读）

| 文档 | 内容 |
|---|---|
| [gold-adjudication-policy.md](gold-adjudication-policy.md) | gold 改动五条件裁定政策 |
| [holdout-live-protocol.md](holdout-live-protocol.md) | holdout/live 冻结与解冻协议（双审签字） |
| [holdout-dual-review-pack.md](holdout-dual-review-pack.md) | holdout 双审材料包 |
| [human-eval-protocol.md](human-eval-protocol.md) | 人评 κ 招募与执行协议 |
| [gold-item-review-log.md](gold-item-review-log.md) | gold 逐题评审日志 |

## 审计与自审

| 文档 | 内容 |
|---|---|
| [AUDIT_REPORT.md](AUDIT_REPORT.md) | 综合审计报告 |
| [audit-scoring-layer.md](audit-scoring-layer.md) | 判分层审计 |
| [audit-task-packages.md](audit-task-packages.md) | 任务包审计 |
| [audit-tests-tools-security.md](audit-tests-tools-security.md) | 测试/工具/安全审计 |
| [calc-hidden-test-report.md](calc-hidden-test-report.md) | calc 隐藏测试报告 |
| [self-review-new-items.md](self-review-new-items.md) · [self-review-new-items-batch2.md](self-review-new-items-batch2.md) · [self-review-new-items-batch3.md](self-review-new-items-batch3.md) · [self-review-new-items-batch4.md](self-review-new-items-batch4.md) | 自拟题分批自审 |
| [expansion-plan.md](expansion-plan.md) | batch5 扩题计划（headroom 低余量包配额与验收门） |

## 运行报告与参数

| 文档 | 内容 |
|---|---|
| [night-report-2026-09-23.md](night-report-2026-09-23.md) | 夜间迭代报告 |
| [sprint-a-report.md](sprint-a-report.md) | Sprint A 收官报告 |
| [run-params-ds-flash-v41.md](run-params-ds-flash-v41.md) · [run-params-ds-flash-v41-c50.md](run-params-ds-flash-v41-c50.md) · [run-params-airac-hard2-r25.md](run-params-airac-hard2-r25.md) · [run-params-glm53flash-subagent-c5.md](run-params-glm53flash-subagent-c5.md) | 各模型/并发档运行参数记录（花费/耗时/得分） |
| [passk-airac-r20.md](passk-airac-r20.md) | a_irac pass^k 运行报表 |
| [calc-real-model-report.md](calc-real-model-report.md) / [fault-dms-real-model-report.md](fault-dms-real-model-report.md) | 真实考生单包报告 |

## 论文材料

| 文档 | 内容 |
|---|---|
| [paper-outline.md](paper-outline.md) | 论文提纲（实验口径与数字锚点） |
| [paper-outline-todos.md](paper-outline-todos.md) | 提纲待办 |
| [paper-numbers.md](paper-numbers.md) | 论文数字溯源清单（数字→来源→机检） |
| [paper-tables.md](paper-tables.md) | 论文表格模板（列 ↔ summary 字段映射） |
| [research-notes.md](research-notes.md) · [research-notes-round2.md](research-notes-round2.md) · [research-notes-round3.md](research-notes-round3.md) | 研究笔记 |
| prompts/ | 隔离测试 agent 提示词等论文复现材料 |

## 实施记录（历史归档）

[impl-P0a.md](impl-P0a.md) · [impl-P0b.md](impl-P0b.md) · [impl-P1.md](impl-P1.md) ·
[impl-P1-rest.md](impl-P1-rest.md) · [impl-P2.md](impl-P2.md) · [impl-P3.md](impl-P3.md) ·
[impl-audit-fix.md](impl-audit-fix.md) —— Sprint A 分阶段实施记录。

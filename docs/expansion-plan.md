# batch5 扩题计划（c281）

> 依据：`reports/headroom-report.md`（3 包低余量）+ `reports/difficulty_emp.json`
> （作者标注与实证脱钩，Spearman ρ=+0.152）+ 用户既定方向：减简单题、加难题、
> 加实务题。本计划是 batch6 之前扩题的**配额准绳**，出题仍须走
> [gold-adjudication-policy.md](gold-adjudication-policy.md) §2 五条件与自审流程。

## 1. 余量诊断（headroom_report 结论）

| 包 | 饱和率 | 实证 p | 余量 | 处置 |
|---|---|---|---|---|
| calc_fail_to_pass | 高 | ≥60% | **低** | 优先补难题 |
| dms_side_effect_intake | 高 | ≥60% | **低** | 优先补难题 |
| u_element_extract | 高 | 75% | **低** | 优先补难题 |
| a_irac_reason | — | 43.18% | 中 | 正常补充实务题 |
| cit_validity | — | — | 中 | stale 族已扩（batch4） |
| long_horizon_case | — | — | 中 | 多轮状态题持续加 |

能力维通过率全景：C 15%（最难）< A 43.18% < U 75% < O 87.5%（饱和）。
**O 维（ ok/not ok 粗判）已无区分度**，新增题一律不再出纯 O 维题。

## 2. 配额（目标：323 → 353，30 题）

| 包 | 新增 | 目标实证通过率 | 形态要求 |
|---|---|---|---|
| calc_fail_to_pass | 8 | 20%–50% | 新法生效/废止/修正交错日的计算题，双日翻转锚 |
| dms_side_effect_intake | 6 | 20%–50% | 多 Fault 注入的沙箱实务题（fault_not_reached/no_recovery 族） |
| u_element_extract | 6 | 25%–55% | 要件抽取含干扰事实（要素缺失/主体错位变体） |
| long_horizon_case | 5 | 30%–60% | ≥8 轮对话，含状态漂移（state_drift）陷阱 |
| a_irac_reason | 5 | 25%–55% | 实务卷宗形态：证据清单+时间线，含红线索 |

## 3. 出题硬约束（每题验收门）

1. **锚引用**：law_anchors 逐字比对 lawkb/text 原文，附 text_hash（来源须为
   国家法律法规数据库/最高法官网）。
2. **难度自评如实填写，但验收以实证为准**：自评 difficulty≥3 而实证
   p≥80% 的题退回重做（作者标注无预测力，见 difficulty_emp）。
3. **目标通过率窗**：新增题 mock 预检后须落在 20%–60% 窗内；
   p>90% 不入库（饱和即无效题）。
4. **每包 10% safety 夹具**与 gold 五条件同批走裁定。
5. **双考生区分度预检**：at/lh/c 三人设中至少两人设得分差 ≥15 分，
   否则说明题面对人设不敏感（背诵题嫌疑）。

## 4. 退场机制（减简单题）

- 实证 p≥90% 且无 hard 变体的存题：移入 `data/archive`（v0.5 Phase 1 先例）。
- rules 基线 ≥90 的题（baseline-report 警告）：逐项归因后改造或退场。
- 退场不改 item_id、不重排行号，MANIFEST 记录退场原因与批次。

## 5. 执行顺序与里程碑

1. **W1**：calc 8 题 + u 6 题（低余量最重）；自审四件套 + text_hash 录入。
2. **W2**：dms 6 题（沙箱夹具设计）+ long_horizon 5 题；双考生预检。
3. **W3**：a_irac 5 题 + 退场清单执行；全量 pytest + ci_gate + MANIFEST 对账
   （353 题）+ dataset-card/CHANGELOG 同步。

> 本文件为计划（非已执行事实）；执行后在本节追加「已完成」标记与 MANIFEST 对账行。

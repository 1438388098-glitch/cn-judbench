# data/archive — 已退场题目归档

本目录存放**已从 public split 退场**的历史题目。这里的题不进 `data/public/MANIFEST.json`
（dataset_content_hash 不覆盖本目录），**不得用于跑分、题量宣称或与 public 题混算**；
保留只为溯源（难度盘点、金样考古、题面演化对照）。

## 归档清单

| 文件 | 题数 | 归档时间 | 归档原因 |
|---|---|---|---|
| `a_irac_reason.jsonl` | 20 | 2026-09-23（v0.5 Phase 1） | a_irac 剖减 32→12：20 题全分饱和（历届考生逐题满分，无区分度）；8 科目×每包网格不变量保留在现役 12 题中 |

## 约定

- 归档题的 `split` 字段保留生成时的 `"public"` 原值（历史记录不改动）——
  **以「文件位于本目录」为归档判据**，字段不作为判据（对照 `data/drafts/README.md`
  的状态机：draft → review → public → archive）。
- 归档/恢复动作须同步更新本表，并在 `CHANGELOG.md` 记账。
- 相关审计口径见 `docs/difficulty-audit-v05.md`（§一 证据白名单、附录 T4a）。

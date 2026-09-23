# data/drafts — 题目草稿区（c318）

> 草稿与正式题库（data/public）**分界严格**：本目录文件不进 MANIFEST、
> 不进任何 run 的判分面。`draft: true` 为硬标记，validate 与判分管线不消费本目录。

## 状态机

```
draft（草稿，本目录） → examinee_round（真考生轮：两名隔离考生作答，
  预期错误模式 ≥1 人触发，见 docs/paper-outline.md §E17 教训）
  → adjudication（gold 裁定：docs/gold-adjudication-policy.md §2 五条件 +
  参考解仲裁） → public（正式入库，MANIFEST 对账） | archive（否决/退场）
```

## 入库硬门（缺一不入）

1. **锚逐字比对**：law_anchors 与 gold 引用必须逐字比对 lawkb/text 原文，
   附 text_hash；来源须为国家法律法规数据库/最高法官网。
2. **双窗翻转验证**：时间效力题用 resolve_article 验证新旧窗解析到位且
   版本不同（tests/test_pipeline_v06.py c302 同口径）。
3. **真考生轮**：两名隔离 subagent 考生独立作答；换答 guard 通过；
   预期错误模式至少一人触发（区分度实证），否则按 E12 负结果归档。
4. **自审四件套** + gold 五条件裁定留痕。

## 现存草稿

| 草稿 | 规格 | 状态 |
|---|---|---|
| a_irac_reason/ah-201.json | at-201（诉讼时效 2→3 年跨总则施行） | awaiting_examinee |
| a_irac_reason/ah-202.json | at-202（继承顺位：继承开始日在民法典前） | awaiting_examinee |
| a_irac_reason/ah-203.json | at-203（借贷利率 4×LPR：受理日错位） | awaiting_examinee |
| a_irac_reason/ah-210.json | at-210（民法典施行前事实适用旧法） | awaiting_examinee |

| cit_validity/ct-201.json | at-201 判定窗（民法总则188@2021-06-01 → wrong_vintage） | awaiting_examinee |
| cit_validity/ct-202.json | at-202 判定窗（继承法10@2021-06-01 → wrong_vintage） | awaiting_examinee |
| cit_validity/ct-203.json | at-203 判定窗（借贷规定25@2014-06-01 → not_yet_effective） | awaiting_examinee |
| cit_validity/ct-210.json | at-210 判定窗（时间效力规定1@2019-06-01 → not_yet_effective） | awaiting_examinee |
| cit_validity/ct-211.json | 规格外对照（时间效力规定1@2021-06-01 → ok，ct-210 对偶窗） | awaiting_examinee |

## ct 系基线预演（R32，2026-09-24）

漂洗后临时集跑同判分管线（确定性，tests/test_draft_baseline_v06.py 锁定）：
mock:gold 5×100 自证；**rules 20.00**——4 个陷阱窗（wrong_vintage/not_yet）
全 0、仅 ct-211 对照窗（ok 判定）满分，「判别非 ok 状态」即本轴全部考点，
均分门禁 ≤40（抬升=泄题前兆，c161 同纪律）；random 首演 48.00（无种子，
ct-201 撞对 wrong_vintage 属单题偶然，不入机检）。真考生轮区分度预期：
合格考生应于 4 陷阱窗满分而 rules 为 0。

规格依据见 docs/expansion-plan.md 附录 B/B-2。三方编号约定：**at-XXX = 规格
id；ah-XXX = 同规格的 a_irac IRAC 叙事草稿；ct-XXX = 同规格的 cit_validity
引用效力判定面草稿**（cit 谓词 status_ladder 只判单窗，故规格双窗拆题）。

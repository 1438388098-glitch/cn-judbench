# CN-JudBench 数据集卡片（Dataset Card, v0.6.0）

- **dataset_version: 0.6.0**（与 `pyproject.toml` / `CITATION.cff` / `CHANGELOG.md` 最新条目同源，一致性有机检）
- **snapshot_date: 2026-09-24** · **license: MIT (code) / CC BY 4.0 (data)**（法条文本为官方作品，见 §7 与 LICENSE 分表声明）
- 快照：2026-09-24 · public split 共 **323 题**（v0.5：Phase 1 剖减 a_irac 全分饱和题 20 题入 data/archive，Phase 3a/3b/3c 新增难题 18+8+10=36 题，Phase 4 新增实务题 30 题；v0.6 batch4 新增 cit stale 族 6 题；原 271；holdout/live 冻结见 docs/holdout-live-protocol.md，本卡不含）
- 口径：题面 schema/适用面校验 `python -m cnjudbench validate` 全过（12 任务包）；
  金样自检基线 v0.6：random 7.96 / rules 27.40 / mock:gold 8 包全 100（reports/runs/baseline-v06c 现行；v0.6 初版 27.03 见 baseline-v06，v0.4.1 历史值 9.03/29.25 见 calc-real-model-report）。
  v0.6 判分效度修复（as_of 强制题面/极性对冲/拒绝否定豁免）重导验证零漂移（baseline-v06b，245 题逐题分一致，tests/test_baseline_zero_drift_v06.py）

## 1. 动机与用途

测出大模型/Agent 在中国司法工作流中「哪一维能用、哪一维危险、是否稳定、代价多少」；
oracle 硬度阶梯（隐藏单测 > 状态 diff > exact > 受约束 F1 > Judge）支持论文级
可复现对比。**不得用于司法裁判、合规放行或当事人决策。**

## 1.1 饱和题标注（v0.6）

68 题带 `saturation_flag: true`（difficulty-audit-v05 T4a/T4b：双考生/三样本实测无区分度，
其中 T4b 60 题尚待第 3 样本复核）。标注**不改变**任何题的金样与主分口径；
发布统计与论文表建议剔除或单列（逐题名单见 reports/difficulty-audit-v05.json
与 data/public/MANIFEST.json 的 difficulty/saturation 字段）。

## 2. 任务包构成（12 包 / 323 题）

| 任务包 | L 层 | oracle | 题数 | 主要能力维 |
|---|---|---|---|---|
| cit_validity | L1 | 机检（引用效力 status_ladder；v0.6 batch4 增 stale 对偶族 6 题：民法总则/继承法废止前后、合同法解释二废止前、刑法修正案九前） | 27 | Cit |
| u_element_extract | L1 | element 抽取（含 hard 34 题；v0.5 Phase 3c 增否定式要件/多日期歧义 6 题） | 49 | U |
| calc_fail_to_pass | L1 | **隐藏单测**（tests/calc/*.py，54 题；v0.5 Phase 3b 增 cx 硬变体 8 题：期间顺延/时效中断/封顶冲抵/复利竞合） | 54 | U |
| s_charge_subsume | L1 | 罪名归并 exact | 20 | S |
| tool_search_statute | L2 | tool_sequence/ast + exact | 26 | G/R/U |
| gaia_fee_deadline | L3a | 金额阶梯 + progress（v0.5 Phase 4a 增时间线综合 6 题） | 23 | K/U |
| dms_side_effect_intake | L3a | **env_diff 终态 diff**（state0 预置 4 题 + 半角镜像 3 题 + v0.5 期限监控 4 题） | 20 | O |
| tool_fault_recovery | L2 | **fault_recovery**（recovery×final；nth=2 进阶 4 + v0.5 nth=3 故障链/部分成功状态判断 4 题） | 16 | O |
| contract_risk | L1 | must_not/风险披露（v0.5 Phase 4c 增风险告知 6 题） | 23 | C |
| a_irac_reason | L1 | 结构化 IRAC（v0.5 重构后 34 题：Phase 1 留存 12 + 时间效力轴 18 + 文书改编 4；原 32 题中 20 题对头部模型全分饱和，移入 data/archive） | 34 | A |
| tau_jud_intake | L3b | 终态 F1 + Proto（多轮；v0.5 Phase 4b 增临期接待 4 题） | 16 | C |
| long_horizon_case | L4 | score–time 多日流程（v0.5 Phase 4a 增六域整案 6 题） | 15 | U |
| （另：dms/fault 冒烟与负例夹具见 reference.md） | | | | |

## 3. 科目与难度分布

- **8 科目全覆盖**：每任务包在 民商事/刑事/合同合规/劳动/家事/知产/行政/执行
  至少各 1 题（validate 网格强制）；民商事为天然大头（诉讼费/利息/期间类计算
  题集中在民商事）。
- **难度**：1–4 级作者标注（1 基础 6 题 / 2 基础-中 81 / 3 中 117 / 4 难 119；batch4 后实测，交叉核验见 test_sample_saturation_v06）；
  实证重标（difficulty_emp，按通过率分带）工具已备（scripts/calibrate_difficulty.py），
  待真实模型数据冻结后回写。
- **来源**（323 题实测分布，机检 c370）：synthetic 305（结构化生成，参数化
  题目+程序化金样）为主；synthetic_adversarial 14 题为对抗注入（干扰段/
  陷阱/负例夹具含 t-fake-001 假调用负例）；real_amended 4 题（at-019..022，
  真实裁定书的**改编**重构题——无任何个人信息，非卷宗原文）。
  **不含任何真实案件卷宗、个人身份信息或受版权保护的文本。**

## 4. 标注与金样质量

- 每题 gold 由生成程序按成文规则独立计算（如隐藏单测期望值生成期硬编码），
  判分管线**不读 gold**（oracle 隔离）；两套真相源一致性由测试锁定
  （`test_gold_consistent_with_hidden_tests` 等）。
- 公平性校验（v0.4）：`answer_enums` 声明的作答枚举必须逐字出现在题面
  （考生须知覆盖判分口径）；canary 每题一枚（sha256 派生 `CNJB-CANARY-*`）。

## 5. 防污染

- 每题 canary 字段进 L1 输出扫描；n-gram 双检（`--ngram-corpus`）对全部题面
  与外部语料做归一化 8-gram 重叠报告（summary.contamination）。
- 生成器脚本全部入库（scripts/add_*.py），题目可由种子重现，支持事后审计。

## 6. 已知局限

1. 合成题为主：语言风格较真实裁判文书规整；真实卷宗纳入需走 holdout 冻结协议。
2. u_element hard 子集对高档模型已近饱和（GLM 实测 82.1% 满分），中间带验收
   应以中档模型为主（见 docs/u-hard-subset-report.md）；a_irac 同样对头部模型
   饱和（hard 复合争点 6/6 满分）——单步识别题无法恢复区分度，true-hard 需
   「要素不点名」事实链题（docs/calc-real-model-report.md §C4）。
3. d-fake-001 类负例夹具对真实模型无区分度（功能为 harness 自检）。
4. 单法官域（劳动/家事等）题量仅满足域覆盖网格，分域细分排名不具统计力
   （§6.1 n 规则以 FRAMEWORK §8.3 两档制为准：n≥100 可排名 / 50≤n<100 报 CI 标 descriptive / n<50 仅描述）。
5. fault 任务 final_exact 口径公平性修正进行中
   （docs/fault-dms-real-model-report.md 发现 2/3）。
6. lawkb 为节录口径（13 法 63 版本；v0.5 增补法释〔2020〕15号 10 条时间效力条文 + 民间借贷16条2021版；2026-09-27 增补诉讼费用交纳办法 13/14 条）：statute 类谓词的判别力受库覆盖约束，
   库外条文分列 unknown_in_lawkb、不记幻觉；扩库准入见 anchor×as_of 审计
   （docs/calc-real-model-report.md §C5）。

## 7. 许可与引用

- 代码 MIT；数据/题面/任务包 CC BY 4.0；lawkb 法条为官方作品（随附 sha256 text_hash 与来源注记）——分表声明见仓库根 LICENSE 尾部。
- **`data/zhuma_fakao/` 不在本数据集声明范围内**：竹马法考历年真题候选池（4139 题），
  仅本地取材用，不入 MANIFEST、不判分、不进论文表；CC BY 4.0 不覆盖该目录，
  处置见 data/zhuma_fakao/README.md。
- 引用格式与版本号以 FRAMEWORK.md 头部为准（v0.6，2026-09-23）。

```bibtex
@misc{cnjudbench2026,
  title  = {CN-JudBench: A Multi-dimensional Benchmark for Large Language Models
            in Chinese Judicial Workflows},
  author = {{CN-JudBench (法衡) Authors}},
  year   = {2026},
  note   = {v0.6, 323 items, 12 task packages; MIT (code) / CC BY 4.0 (data)},
  url    = {https://github.com/TODO-assign-repo}
}
```

> GitHub 引用入口：仓库根 `CITATION.cff`（cff 1.2.0，与上表同源，版本一致性有机检）。

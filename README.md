# CN-JudBench（法衡）

中国司法多维度大模型 / 司法 Agent 评测框架（**v0.4**：Sprint A 计分架构 + 统计协议 + 隐藏单测 oracle 已落地）。

**目标**：测出模型在中国司法工作流里「哪一维能用、哪一维危险、是否稳定、代价多少」。  
**分数**：百分制，保留两位小数（0.00–100.00）。  
**非法律意见**：评测结果不得用于司法裁判、合规放行或当事人决策。

## 文档

| 文件 | 说明 |
|---|---|
| [FRAMEWORK.md](FRAMEWORK.md) | 框架设计定稿 **v0.4**（§14：v0.3.1→v0.4 差异清单） |
| [docs/DESIGN-benchmark-optimization-v0.4.md](docs/DESIGN-benchmark-optimization-v0.4.md) | 优化设计（对标映射 + Sprint A/B/C） |
| [docs/paper-outline.md](docs/paper-outline.md) | 论文骨架与差距清单 |
| [index.html](index.html) | 设计文档可读版（浏览器预览） |
| [docs/research-notes.md](docs/research-notes.md) | 第一轮调研：中文法律评测 |
| [docs/research-notes-round2.md](docs/research-notes-round2.md) | 第二轮调研：coding / agent / 工程硬化 |
| [docs/impl-P0a.md](docs/impl-P0a.md) | **P0a 实施文档**（lawkb + 校验 + 冒烟任务包） |
| [docs/impl-P0b.md](docs/impl-P0b.md) | **P0b 实施文档**（FTP/PTP + CiteGuard + API/Manifest） |
| [docs/impl-P1.md](docs/impl-P1.md) | **P1 实施文档**（Judge / 红线 / 门禁） |
| [docs/impl-P1-rest.md](docs/impl-P1-rest.md) | **P1 收尾**（Judge 进 runner / CI 门禁） |
| [docs/impl-P2.md](docs/impl-P2.md) | **P2 实施文档**（工具沙箱 / Tool-Bench / Legal-GAIA） |
| [docs/impl-P3.md](docs/impl-P3.md) | **P3 实施文档**（τ-Jud / 合同轨 / IRAC / Long-Horizon） |

## 项目状态

- [x] 设计与调研（v0.3.1，含外部审查修订）
- [x] **P0a 实施文档**（`docs/impl-P0a.md`）
- [x] **P0a 代码** lawkb 多版本解析 + 题面/谓词校验 + `cit_validity` 冒烟（60 项测试）
- [x] **P0b 实施文档**（`docs/impl-P0b.md`）
- [x] **P0b 代码** FTP/PTP 执行器 + CiteGuard + API adapter（104 项测试）
- [x] **P1 实施文档**（`docs/impl-P1.md`）
- [x] **P1 代码** Judge/Abst/红线/诊断掉分/bootstrap/$/solve/canary（114 项测试）
- [x] **P1 收尾代码** `--with-judge` 进 runner + 机检/Judge 分列 + limits.md + holdout 守卫 + CI 门禁（133 项测试，`scripts/ci_gate` 全绿）
- [x] **P2 代码** 6 工具沙箱 + Legal-Tool-Bench（L2 19 题，假调用零分）+ Legal-GAIA 精品 10 题（L3a exact + progress）+ 轨迹 hash 进 manifest（156 项测试）
- [x] **P3 代码** τ-Jud（user_script + 终态 F1 + Proto + pass^k 双列/方差分解）+ 合同轨 + IRAC + Long-Horizon + `run-dialog`（175 项测试）
- [x] **v0.4 Sprint A** safety/capability 分列 + status_ladder/金额阶梯/must_not + partial-only 基数 + over_refuse×0.50
- [x] **v0.4 统计协议** bootstrap CI / pass^k 组合语义 / report.csv / 正式分 provisional 门禁 / n-gram 污染双检（ci_gate 第 7 步守门）/ random·rules 基线同管线
- [x] **v0.4 新任务** calc_fail_to_pass 46 题（隐藏单测 oracle，五公式：受理费/单利/期间/半年复利/保全费，hard 变体考节假日顺延与封顶规则）+ u_element hard 子集 28 题（GLM 实测 82.1%，见 docs/u-hard-subset-report.md）+ dms_side_effect_intake 16 题（env_diff 终态 diff；state0 预置「在办案件」与双卡分心）+ tool_fault_recovery 12 题（§5.4 四型故障注入 recovery×final + R22 nth=2「先成功后故障」进阶 4 题）
- [x] **v0.4 翻转实证** GLM 考生模式 k=3 复测：逐对题级翻转 6/11≈55% ≫ 5% 门禁（docs/u-hard-subset-report.md 追加节）→ 单样本 run 一律 provisional，主表强制 pass^k
- [x] **v0.4.1 测量效度审计** 金样法学复核消融（同答案重判 31.58→86.84，acceptable_articles any-of 多解口径）· 基线泄题修复与扫描（law_anchors 判分锚禁入基线，a_irac random/rules 96→12）· lh-06 锚点时效修正（继承法10 带废止窗口）· lawkb v0.4.1 扩库（12 法 51 版本）· v0.4.1 基线表（random 9.03 / rules 29.25 / mock:gold 8 包全 100，见 docs/calc-real-model-report.md §C5） · E12+ 要素不点名实测（ah-101..104 仍饱和，as_of 版本选择是唯一实质错因）· E15 引用括注假阴性修复（2/29 题误罚 50→100，引用侧剥尾括注）
- [x] **v0.5 难度重构 Phase 1+2a** 全库四级盘点（38 实难 / 88 砍候选 / 143 待测，docs/difficulty-audit-v05.md）· a_irac 剖减 32→12（20 题全分饱和入 data/archive，8 科目×每包网格不变量保留）· lawkb 增补法释〔2020〕15号时间效力规定 10 条（12 法 60 版本，公报官方文本 + 逐条 text_hash 可事后核，docs/sources/spc_civil_temporal_2020_gongbao.html）
- [ ] 待办：DS v0.4 复跑（密钥）· holdout 冻结执行（协议已备）· 人评 κ 试点（方案已备）· v0.5 Phase 2b-3 难题/实务题扩容（DESIGN §3-§4）

## 快速开始（5 分钟）

```bash
py -3.13 -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q                 # 296 项测试全绿
.venv/Scripts/python -m cnjudbench run-all   --tasks cit_validity,dms_side_effect_intake,tool_fault_recovery   --model mock:gold --out reports/runs/demo
cat reports/runs/demo/report.csv                  # §6.1 论文表直贴列
```

换真实模型：`--model openai:<model> --base-url …`（密钥仅经环境变量）；已有答案文件用
`--model file:<answers 目录>` 回灌（全管线同 API 跑法，见 docs/paper-outline.md §7）。

## 如何跑（完整）

```bash
# 环境：Python 3.11+，装依赖与包
py -3.13 -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"

# 校验任务包与题面（schema + §4.2.1 适用面矩阵 + lawkb 完整性）
python -m cnjudbench validate --items data/public --tasks tasks

# 按 as_of 解析法条版本（附录 D.4：四态 + 条文文本）
python -m cnjudbench resolve-law --law 刑法 --article 264 --as-of 2024-06-01

# cit_validity 冒烟：金样期望 vs 解析器对照（不调用模型）
python -m cnjudbench smoke-cit-validity

# 机检跑分（P0b）：离线金样 Mock 或 OpenAI-compat 端点
python -m cnjudbench run --task cit_validity --model mock:gold --out reports/runs/smoke-cit
python -m cnjudbench run-all --tasks cit_validity,u_element_extract,s_charge_subsume --model mock:gold
#   --model openai:<model> --base-url … 走真 API（密钥仅经 OPENAI_API_KEY / CNJUD_API_KEY 环境变量）
# 产出 reports/runs/<run_id>/summary.json + manifest.json + limits.md（百分制两位小数；目录已 gitignore）

# 机检 + Judge 分列（P1）：--judge mock|openai；缺 rubric 的任务 judge 列为 n/a（禁填 0.00）
python -m cnjudbench run-all --tasks u_element_extract --model mock:gold \
  --with-judge --judge mock --out reports/runs/j1
#   --blend weighted 才显式加权（0.7 机检 + 0.3 Judge），默认 parallel 分列不混分

# L2 工具调用 / L3a 多步（P2）：mock:tools 重放 gold 调用轨迹，mock:gold 出 exact 终答
python -m cnjudbench run --task tool_search_statute --model mock:tools --out reports/runs/t1
python -m cnjudbench run --task gaia_fee_deadline --model mock:gold --out reports/runs/g1
#   产出 items/<id>.trajectory.json（工具轨迹），hash 进 manifest.tools.trajectory_hashes

# P3：合同轨 / IRAC / Long-Horizon（L1/L4 机检）
python -m cnjudbench run --task contract_risk --model mock:gold --out reports/runs/c1
python -m cnjudbench run --task a_irac_reason --model mock:gold --out reports/runs/a1
python -m cnjudbench run --task long_horizon_case --model mock:gold --out reports/runs/l4

# P3：τ-Jud 多轮（run-dialog）——user_seed / model_seed 分列，pass^k 固定用户 vs 换 persona
python -m cnjudbench run-dialog --task tau_jud_intake --model mock:dialog \
  --user-seed 42 --k-pass 3 --out reports/runs/tau1
#   summary.stability：pass_k_fixed_user / pass_k_swapped_persona / variance（model|user_script|judge）
#   律师基线缺失时写「未测」，禁止编造对照

# CI 门禁（validate + pytest + mock run-all + 产物断言 + 复跑翻转率=0）
bash scripts/ci_gate.sh          # Windows: powershell -File scripts/ci_gate.ps1
python scripts/flip_rate_check.py --tasks cit_validity --model mock:gold   # API 建议阈值 < 5%
```

Mock（`mock:gold`）零网络、确定性，CI 只跑 Mock；真 API 冒烟为可选步骤。

# v0.4：答案回灌与统计协议
# 1) 回灌判分（不调 API）：导出题面 → 外部生成 answers/<item_id>.txt → file: 模型官方判分
python scripts/export_prompts.py --tasks u_element_extract --run-dir runs/u1
#   （答案放 runs/u1/answers/ 后）
python -m cnjudbench run-all --tasks u_element_extract --model file:runs/u1 --out reports/runs/u1-scored

# 2) 翻转率门禁（同一模型两跑，API 建议 max-flip 0.05；超门禁 → provisional，不进正式表）
python scripts/flip_rate_check.py --tasks u_element_extract --model openai:<model> --max-flip 0.05

# 3) n-gram 污染双检（对全部题面扫描与语料重叠比，报告入 summary.contamination）
python -m cnjudbench run-all --tasks u_element_extract --model mock:gold   --ngram-corpus docs/corpus.txt --ngram-size 8 --out reports/runs/n1

# 4) 论文表生成：正式表（T-main）只收 provisional=false，其余进附录 T-provisional
python scripts/make_paper_tables.py --runs reports/runs --out docs/paper-tables.md

# 4b) pass^k 多 run 聚合（组合语义 + bootstrap CI + flip 门禁提示，同模型 ≥k 个 run）
python scripts/aggregate_passk.py --runs reports/runs/ds-a reports/runs/ds-b reports/runs/ds-c   --threshold 100 --out docs/passk-ds.md

# 5) 案管副作用任务（env_diff 终态 diff；d-101..104 为 state0 预置在办案件，d-104 双卡分心）
python -m cnjudbench run-all --tasks dms_side_effect_intake --model mock:tools --out reports/runs/dms1

# 6) 人评一致性（加权 κ + bootstrap CI + 与机检 spearman）
python scripts/kappa.py --ratings ratings.csv --machine machine.csv

## 测试

```bash
.venv/Scripts/python -m pytest -q
```

## 如何加题

1. 在 `tasks/<task_id>/` 建任务三件套：`task.yaml` + `predicates.yaml` + `reference.md`（主观另加 `rubric.yaml`）。  
2. 题面放 `data/public|holdout|live/*.jsonl`，字段见 FRAMEWORK 附录 C。  
3. 谓词必须符合 §4.2 的 **output_type 闭合枚举与适用面**；`composite` 必填 `components`；`hcut` 只能是 `Cit/Abst/Hall/Cons/Proto`。  
4. 法条锚点写全称 + `as_of`，依赖 lawkb 多版本解析（附录 D）。  
5. 通过 schema 校验与 Verified 状态机后再进 `active`。

## 目录

```text
src/cnjudbench/  # 包：lawkb 解析 / schemas / validate / scale / smoke / predicates / citeguard / adapters / runner / judge / metrics / gates / contamination / report / tools / cli
lawkb/           # 法条时间轴多版本（生成脚本 scripts/build_min_lawkb.py）
tasks/           # 任务包（cit_validity / u_element_extract / s_charge_subsume / tool_search_statute / gaia_fee_deadline）
data/            # public / holdout（ignore） / live
tests/           # pytest
docs/            # 调研、实施文档与校准集
reports/runs/    # 每次评测的 manifest + summary + limits.md + items/*.trajectory.json（gitignore）
```

## 许可

- 代码：待定（建议 MIT）。  
- **数据 / 题面 / lawkb 文本与代码分表声明**；引用外部数据集前先核对其 LICENSE（见 FRAMEWORK §10）。

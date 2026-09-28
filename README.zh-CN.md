[English](./README.md) · 简体中文

# CN-JudBench（法衡）

中国司法多维度大模型 / 司法 Agent 评测框架（**v0.6**：补判分效度与反刷分——tau 部分得分、set_f1 1-1 反倾倒、any-of 双口径与分包基线守门；新增 `cnjudbench compare`（bootstrap CI + McNemar + 预注册六包 macro/micro）与 gold 改判预注册政策、MIT/CC BY 4.0 分表许可；完整历史见 [CHANGELOG.md](CHANGELOG.md)，版本真源 = [FRAMEWORK.md](FRAMEWORK.md) 头部）。

**Abstract (EN)**: CN-JudBench evaluates large language models on Chinese judicial
workflows across 12 task packages (323 public items) spanning citation validity,
element extraction, calculation with hidden unit tests, charge subsumption,
tool invocation with fault injection, multi-turn intake and multi-day case
management. Scoring is machine-checked at the predicate level with a registered
failure taxonomy, contamination canaries, random/rules baseline leak monitoring,
and a preregistered statistical protocol (pass^k combinational semantics, paired
bootstrap CIs, McNemar exact tests, two-tier ranking granularity). Version 0.6
closes three scoring-validity gaps found via live examinee rounds: free-text
state predicates now award partial credit, reward-hacking via answer dumping is
blocked by one-to-one set matching, and per-package baselines guard against
scoring shortcuts. Code is MIT-licensed; the public split is CC BY 4.0
(see CITATION.cff).

- **目标**：测出模型在中国司法工作流里「哪一维能用、哪一维危险、是否稳定、代价多少」。
- **分数**：百分制，保留两位小数（0.00–100.00）。
- **非法律意见**：评测结果不得用于司法裁判、合规放行或当事人决策。

## 任务包速览（12 包 / 323 题，机检对账 MANIFEST）

| 任务包 | 题数 | 主能力维 | oracle |
|---|---|---|---|
| calc_fail_to_pass | 54 | U | 隐藏单测 |
| u_element_extract | 49 | U | element 抽取 |
| a_irac_reason | 34 | A | 结构化 IRAC |
| cit_validity | 27 | Cit | 引用效力 status_ladder |
| tool_search_statute | 26 | G/R/U | tool_sequence/ast |
| contract_risk | 23 | C | must_not/风险披露 |
| gaia_fee_deadline | 23 | K/U | 金额阶梯+progress |
| dms_side_effect_intake | 20 | O | env_diff 终态 |
| s_charge_subsume | 20 | S | 罪名归并 exact |
| tau_jud_intake | 16 | C | 终态 F1+Proto |
| tool_fault_recovery | 16 | O | recovery×final |
| long_horizon_case | 15 | U | score–time 多日 |

## 跑分一览

所有对外报分走同一条判分管线，并登记于 [docs/run-score-ledger.md](docs/run-score-ledger.md)——唯一汇总账。

- **基线锚点**（同判分口径，`baseline-v06c`，2026-09-25 重导）：random **7.96** · rules **27.40** · mock:gold **100.00**。`mock:gold` 是金样答案回放判分管线，100.00 为管线天花板与健康门禁，**不是**模型分数。
- **真考生轮**（v0.5 Phase 5，双隔离考生 ×62 题）：pass^2 = **46.77** [33.87, 59.68]（docs/paper-outline.md §9，E17）。
- **现行模型榜**：13 条全量行（n_capability=238 · n_safety=7），主指标 = 总分（包等权，`capability.grand_eq`；加权总分仅参考）。**全部行为 provisional=true**，待 flip（<5%）门禁——仅可作描述性对照，不得作正式排名引用。逐 run 明细：docs/run-score-ledger.md §1；可视化面板：[index.html](index.html)。

## 快速开始（5 分钟）

```bash
# 1) 建 venv 并安装依赖与包（含 pytest/pydantic/PyYAML）
# Windows:
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
# Linux/macOS:
# python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"

# 2) 跑测试（630+ 项测试全绿；精确计数见 CI，勿在 README 硬编码）
# Windows 用 .venv\Scripts\python；Linux/macOS 用 .venv/bin/python
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m cnjudbench run-all   --tasks cit_validity,dms_side_effect_intake,tool_fault_recovery   --model mock:gold --out reports/runs/demo
cat reports/runs/demo/report.csv                  # §6.1 论文表直贴列（solve% 为保守口径：n/a 计未解决）
```

> 运行约束：本包按「克隆仓库根目录运行」设计——`tasks/`、`data/public/`、
> `lawkb/`、`configs/` 为仓库根资产，不随 pip 包分发；请在克隆根目录执行命令。

换真实模型：`--model openai:<model> --base-url …`（密钥仅经环境变量）；已有答案文件用
`--model file:<answers 目录>` 回灌（全管线同 API 跑法，见 docs/paper-outline.md §7）。
  回灌前必跑换答对齐 guard：`python scripts/check_answer_alignment.py --run-dir <run 目录>`（bigram Dice + 反向最佳确认；SUSPECT 清单人工复核，已两次抓到 subagent 答案错位事故）。

两 run 配对比较（排名主张必带 CI 与 p 值；排名用 `--preregistered` 六包等权口径）：

```bash
# A/B 换成两个真实 run 目录（如 reports/runs/ds-flash-v06-full）；reports/runs/ 不入库
.venv/Scripts/python -m cnjudbench compare --run-a <run-A> --run-b <run-B>     --preregistered --items-out reports/compare/items.csv
# 输出：micro diff±CI + McNemar p；preregistered 时另报 macro(六包等权) diff±CI
```

## 如何跑（完整）

```bash
# 环境：Python 3.11+，装依赖与包
# Windows:  py -3.13 -m venv .venv
# Linux/macOS:  python3 -m venv .venv


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

## 答案回灌与统计协议（v0.4）

```bash
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

# 7) 成对比较（bootstrap CI + McNemar；--preregistered 只比核心六包，macro 六包等权）
python -m cnjudbench compare --run-a reports/runs/m1 --run-b reports/runs/m2 --preregistered
#   summary.report 的 solve% 为保守口径（n/a 计未解决），与 scored%（n/a 剔除）并列读
```

## 新增题目流程（draft → public）

草稿写入 `data/drafts/`（`draft: true` 硬标记，不进 MANIFEST）→ 两名隔离真考生作答（预期错误模式须实证触发，E17 教训）→ gold 五条件裁定（docs/gold-adjudication-policy.md §2）→ 官方锚文本逐字比对 + text_hash → 正式入库并 MANIFEST 对账。

> 命令跨平台：Windows 用 `.venv/Scripts/python`，Linux/macOS 等价 `.venv/bin/python`（或激活 venv 后直接 `python`）。

## 如何加题

1. 在 `tasks/<task_id>/` 建任务三件套：`task.yaml` + `predicates.yaml` + `reference.md`（主观另加 `rubric.yaml`）。  
2. 题面放 `data/public|holdout|live/*.jsonl`，字段见 FRAMEWORK 附录 C。  
3. 谓词必须符合 §4.2 的 **output_type 闭合枚举与适用面**；`composite` 必填 `components`；`hcut` 只能是 `Cit/Abst/Hall/Cons/Proto`。  
4. 法条锚点写全称 + `as_of`，依赖 lawkb 多版本解析（附录 D）。  
5. 通过 schema 校验与 Verified 状态机后再进 `active`。

## 测试

```bash
.venv/Scripts/python -m pytest -q
```

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

## 文档

| 文件 | 说明 |
|---|---|
| [docs/technical-report.md](docs/technical-report.md) | **技术报告 v1**（设计、判分协议、效度控制、统计协议、当前结果诚实口径） |
| [docs/gold-adjudication-policy.md](docs/gold-adjudication-policy.md) | 金样验收与改判预注册规则（改 gold 必读） |
| [FRAMEWORK.md](FRAMEWORK.md) | 框架设计总纲（版本真源，头部现为 **v0.6**） |
| [docs/DESIGN-benchmark-optimization-v0.4.md](docs/DESIGN-benchmark-optimization-v0.4.md) | 优化设计（对标映射 + Sprint A/B/C） |
| [docs/paper-outline.md](docs/paper-outline.md) | 论文骨架与差距清单 |
| [index.html](index.html) | 跑分记分册可视化面板（浏览器预览） |
| [docs/research-notes.md](docs/research-notes.md) | 第一轮调研：中文法律评测 |
| [docs/research-notes-round2.md](docs/research-notes-round2.md) | 第二轮调研：coding / agent / 工程硬化 |
| [docs/research-notes-round3.md](docs/research-notes-round3.md) | 第三轮：判分反刷分与统计口径审计台账（45 条处置） |
| [docs/lawkb-ingest-queue.md](docs/lawkb-ingest-queue.md) | 法条库逐字校对入队清单（官方文本 + text_hash） |
| [docs/self-review-new-items-batch4.md](docs/self-review-new-items-batch4.md) | batch4 六题（cit-022..027）自审与基线扫描，待用户批准 |
| `reports/baseline-report.md` | 基线分布与接近满分警告（R17 泄题监控常驻化） |
| `reports/headroom-report.md` | 扩题/削题余量报告（饱和率×rules×实证 p） |
| `reports/repro-inventory.md` | paper-outline 引用资产存在性盘点 |
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
- [x] **v0.5 难度重构 Phase 1+2a+3a+3b+3c+4** 全库四级盘点（38 实难 / 88 砍候选 / 143 待测，docs/difficulty-audit-v05.md）· a_irac 剖减 32→12（20 题全分饱和入 data/archive，8 科目×每包网格不变量保留）· lawkb 增补法释〔2020〕15号时间效力规定 10 条（12 法 61 版本，公报官方文本 + 逐条 text_hash 可事后核，docs/sources/spc_civil_temporal_2020_gongbao.html）· 时间效力轴难题 18 题（at-001..018：新旧法衔接 8/程序时效交叉 5/民间借贷三版 5，as_of 驱动版本解析，负例已验证）· 计算硬变体 8 题（cx-001..008：期间顺延/时效中断/封顶冲抵/复利竞合，隐藏单测 oracle + 陷阱值负例验证）· 抽取与工具进阶 10 题（u-044..049 否定式要件/多日期 + f-105..108 nth=3 故障链/部分成功状态判断）· 实务题 30 题（gaia 时间线 6/lh 六域整案 6/dms 期限监控 4/tau 临期接待 4/contract 风险告知 6/文书改编 4；4e Judge 写作轨按风险条款 defer）· Phase 5 双隔离考生 ×62 题实测（pass^2=46.77，at/lh/c 三族有效区分；环内修复 4 处金样/题面缺陷：at-019 锚 25→16、at-022 锚 27→1+acc19、cx-007 期望值 7470→11863.40、tau 题面显式化；lawkb 61 版本，docs/paper-outline.md §9 E17）
- [ ] 待办：DS v0.4 复跑（密钥）· holdout 冻结执行（协议已备）· 人评 κ 试点（方案已备）· f-105..108 工具轨真考生实测（需 API 轮）· tau 真考生扩样（v0.6 部分得分判分已实测可区分，见 paper-outline E18）

## 许可

- 代码：MIT（见 LICENSE）。  
- 数据 / 题面 / 任务包：CC BY 4.0；lawkb 法条文本为官方作品（著作权法第五条不适用著作权保护），随附 sha256 text_hash 与来源注记（分表声明见 LICENSE.DATA）。

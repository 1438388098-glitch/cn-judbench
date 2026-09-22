# CN-JudBench（法衡）：中国司法多维度大模型评测框架

> **v0.4** · 计分架构升级落地（Sprint A 已实现；依据 `docs/DESIGN-benchmark-optimization-v0.4.md`）  
> 前序证据：`docs/research-notes.md` · `docs/research-notes-round2.md`  
> v0.2→v0.3：外部设计审查修订——补 **lawkb schema**、**PTP×output_type 适用面**、**manifest 与时间切片一致性**；明确 **百分制、两位小数**；收紧 Judge 成本、排名粒度、防作弊适用面与伦理/许可边界。  
> v0.3→v0.3.1：闭合 `output_type` 枚举（含 `composite`/`tool_call`/`exact`）；写明 Hall 题级扣分与维度折减**计算顺序**；manifest 示例 `k_pass` 对齐 §8.2；清理 HTML 实体。  
> v0.3.1→v0.4：**safety/capability 分列**（Item.role，夹具出主分）；**oracle 硬度阶梯**（status_ladder 分档 / 金额相对误差阶梯 / fail_to_pass·env_diff 预留）；**中间带原则**（满分≤25%、contains 0.80、must-not 门禁、over_refuse×0.50）；**compose_score 重定义**（partial 计分、zero/cap 门禁不进基数）；**baselines 两列**（random/rules 同管线）；**统计协议**（bootstrap CI / flip 门禁 / 组合 pass^k / 正式分 provisional 契约）；**难度实证标定**。差异逐条见 §14。

---

## 0. 一句话定位

**CN-JudBench** 不是「再堆一套法考题」，而是一套：

> **以司法能力 8 维为骨架 · 以可执行判分谓词为 oracle · 以静态 QA → 工具 → 轨迹 → 带状态协议为金字塔 · 以引用可信与执业红线为横切**  
> 的个人可维护评测框架——回答：  
> 「这个模型/司法 Agent 在中国司法真实工作流里，**哪一维能用、哪一维危险、是否稳定、花了多少钱**？」

### 评分总则（强制）

| 规则 | 约定 |
|---|---|
| 刻度 | **百分制**：一切维度分、任务分、横切子分、总览指数均映射到 **0.00–100.00** |
| 精度 | **保留两位小数**（四舍五入，round-half-even）；原始机检计数可另存，报表只出两位 |
| 禁止 | 不以 0–1、0–5、A/B/C 作为对外分数；内部 rubric 原始刻度须先线性/分段映射到百分制 |
| 缺失 | 不可评记 `null` 并在报告标 `n/a`，**禁止填 0.00 充数** |
| 对比 | 同题配对比较时，先算百分制分差，再报 bootstrap 95% CI（单位：分） |

**常用映射**（实现时写死进 `metrics/scale.py`，禁止各任务私自换算）：

```text
acc/F1/EM/NDCG 等 ∈ [0,1]     → score = 100 * value
rubric 维度 0–4                → score = 25 * value          # 0/25/50/75/100
rubric 维度 0–5                → score = 20 * value
NLD（越小越好）                → score = 100 * max(0, 1 - NLD)
gate 触发（幻觉条文等）         → 该题 score = 0.00（一票否决）
gate 封顶（cite 不达标）        → 该题 score = min(score, 50.00)  # 可按 rubric 配置
```

**报告展示**：维度雷达、任务表、模型对比表一律 `xx.xx`；同时附 `n` 与 CI。分数排序用未舍入值，展示用两位小数。

---

## 1. 设计原则（十条硬约束 / 戒律）

1. **先 taxonomy，后题量** — 无「维×难度×角色×域×交互层」标签不入库。  
2. **双集判分（司法版 unit test）** —  
   - **FTP（应命中）**：必须出现的要件、法条、判项字段、风险提示；  
   - **PTP（不得破坏）**：已正确字段/引用/结构不被改坏（**仅限可机检范围，见 §4.2 矩阵**）。  
3. **锚点可机检优先** — 说理与风格进 Judge 层，**绝不与机检混成一个数**；自由文本的「不得破坏」不进机检 PTP，改由结构化抽取后再判或入 rubric gate。  
4. **引用是一等公民（CiteGuard）** — claim 级落库核验（存在 / 条号 / 时效）；防 Right-Answer-Wrong-Reason。  
5. **交互分层清晰（L1–L4）** — 禁止用 L1 分冒充「可部署」。  
6. **环境钉死可复现** — lawkb **按 as_of 取切片**、工具沙箱、prompt_hash、model revision、harness SHA 全进 manifest（见 §7.1）。  
7. **抗污染分层（注意适用面）** — canary / 时间切片 Live / 私有 holdout + 限流对所有模型有效；**Min-K% 等 logit 检测仅开源权重**（见 §9）。  
8. **稳定性与成本同级** — pass^k、$/solve、p95 latency 与正确率并列；**Judge 调用次数进成本账本**。  
9. **过度拒答与危险作答对偶惩罚** — Abst 双标签。  
10. **个人可运维 + 诚实边界** — 数据 SemVer；报告固定「非法律意见」声明；代码许可 ≠ 数据许可；评测题面伦理约束见 §12。

---

## 2. 评测金字塔（从静态到 Agent）

```text
L4  整案/长程 casework     ── 分数–时间曲线（律师基线可选，见 §12.3）
L3b 带状态对话/流程 τ-Jud  ── 政策手册 + 模拟用户 + 案卡终态 + pass^k
L3a 多步轨迹 Legal-GAIA   ── 卷宗包 + 工具链 + exact 终答 + progress
L2  工具调用 Tool-Bench   ── AST/参数/是否该调/假调用检测
L1  静态知识/推理          ── 8 维 QA / 抽取 / 预测 / 说理
底座 lawkb(Appendix D) · 文书 schema · 计算金样 · 执业规则文本 · 工具沙箱
```

**个人路线**：L1 必做 → L2 小工具集必做 → L3a 选做精品 → L3b/L4 有余力再上。

---

## 3. 能力 Taxonomy

| 代码 | 维度 | 典型任务 | 默认 oracle | 典型 output_type |
|---|---|---|---|---|
| **K** | 法律知识记忆 | 法条/解释/术语 | acc, acc_norm | choice, short |
| **U** | 文理与要素抽取 | NER、焦点、金额、期间 | EM / 字段 F1 | extract |
| **R** | 规范识别与检索 | 法条推荐、类案排序 | NDCG / MRR + 时效 | rank, choice |
| **S** | 事实涵摄（三段论） | 罪名/案由、要件符合 | 要件命中 F1 | structured |
| **A** | 争点与论证 | 争点、攻防、上诉理由 | IRAC-Recall + Judge | gen |
| **O** | 结果与量刑 | 刑期、胜负、改判 | NLD + 幅度命中 | regress, choice |
| **G** | 文书生成与说理 | 说理段、摘要、代理词 | lint + rubric + Cite | gen |
| **C** | 角色沟通与风险 | 咨询、风险、普法 | rubric + Abst + 终态 | gen |

**角色**：法官 / 检察官 / 律师 / 法务 / 当事人。  
**域**：刑事 / 民商 / 婚姻家事 / 劳动 / 行政 / 知产 / 执行 / 合同合规。  
**难度** `difficulty`：1记忆 – 2理解 – 3适用 – 4评价创造（**与 `interaction` L1–L4 字段分离**）。

### 3.1 横切红线（`hcut` 值域）

`hcut` 为数组，元素**只能**取：

| 值 | 含义 | 典型扣分（百分制） |
|---|---|---|
| `Cit` | 引用真伪/条号/时效 | 幻觉条文 → 本题 0.00；stale/wrong_vintage/错误时效 → 本题 0.00 |
| `Abst` | 应拒 / 应答 | 危险承诺 → 本题 0.00 且 safety_flag；过度拒答 → 本题 ×0.50 |
| `Hall` | 编案号/编案例/编金额 | 每处重大幻觉 −20.00 分/题，下限 0.00（题级；与维度级折减的顺序见 §8.1） |
| `Cons` | 同案多跑一致 | 并入 pass^k / 结论漂移，不单题扣 |
| `Proto` | 执业协议（L3b） | 见 §5.1，违规项 gate |

---

## 4. 判分谓词模型

### 4.1 题面结构

```text
Item = 多维标签 + prompt
     + predicates { ftp[], ptp[], diagnostic_ftp[]? }
     + gold / law_anchors / as_of
     + rubric? / state_goal?
     + canary / split(public|holdout|live)
     + contamination_risk / source
```

### 4.2 PTP / FTP 谓词 × output_type 适用面（戒律 2/3 闭环）

#### 4.2.0 `output_type` 闭合枚举（强制）

以下 **10 个值** 为合法全集，JSON Schema `enum` 与此表逐字一致。**禁止**再发明 `mixed`、`extract+gen` 等未定义值。

| 值 | 含义 | 典型任务 |
|---|---|---|
| `choice` | 单选/多选 | 法考客观、场景选择 |
| `short` | 短答案（可别名等价） | 术语、条号摘要 |
| `extract` | 字段/跨度抽取 | NER、金额、期间 |
| `structured` | 结构化 JSON（schema） | 罪名+要件、引用列表 |
| `rank` | 排序/检索列表 | 类案、法条候选 |
| `regress` | 数值回归 | 刑期月数 |
| `gen` | 自由文本生成 | 说理、咨询、文书段 |
| `exact` | 严格 exact 终答（GAIA 式） | 条号、金额、单一短语 |
| `tool_call` | 工具调用轨迹（L2） | search_statute / calc_fee |
| `composite` | **多段复合**；必须另填 `components[]` | extract+gen、应拒/应答混题 |

**复合任务**：`output_type: composite`，且 `components` 为上述单型的非空数组（如 `["extract","gen"]`、`["choice","gen"]`）。判分按 `components` 各自适用面执行后加权（默认等权，任务包可改）。

**历史错误值映射（一次性，禁止再用）**：

| 错误值 | 改为 |
|---|---|
| `mixed` | `composite` + `components` |
| `extract+gen` | `composite` + `components: ["extract","gen"]` |
| （裸写）`tool_call` / `exact` | 合法，见上表 |

#### 4.2.1 谓词适用面矩阵

**原则**：FTP/PTP **只对机检可判定的输出型开放**；自由文本不得写机检 PTP。`composite` 取其 `components` 的逻辑与（仅对声明了的段生效）。

| 谓词类型 | choice | short | exact | extract | structured | rank | regress | gen | tool_call |
|---|---|---|---|---|---|---|---|---|---|
| `statute` / `must_not_statute` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* |
| `element` / `field`（FTP） | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✗ | ✓（终答段） |
| `field_keep`（PTP） | — | — | — | ✓ | ✓ | — | — | ✗ | — |
| `amount` / `deadline` | — | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✗ | ✓ |
| `schema` / `lint` | — | — | — | ✓ | ✓ | — | — | ✓（栏目级） | ✓（参数 AST） |
| `state`（终态 diff） | — | — | — | — | ✓ | — | — | ✗ | ✓（工具副作用） |
| `tool_sequence` / `tool_ast`（PTP）／`fake_tool`（FTP） | — | — | — | — | — | — | — | ✗ | ✓（P2 工具轨迹） |
| `risk_disclosure` / `refuse` / `no_fabrication` | ✓ | — | — | — | ✓ | — | — | ✓* | ✗ |
| `progress_keyword` | — | — | ✓（弱） | — | — | — | — | ✓（弱） | ✓（弱） |
| `custom_script` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓（脚本自负） | ✓ |

\* 在 `gen` / `tool_call` 上：**先结构化抽取 claim，再机检**；抽不到 claim 时降级为 rubric gate，**不得**对原文做脆弱正则。`exact` 机检优先，不设自由文本 PTP。

**P2 工具轨迹判分**（impl-P2 §3/§6）：`fake_tool`（FTP，zero）管「该调未调/虚构调用/调了未注册工具」；
`tool_sequence`（PTP，partial）管期望工具子集覆盖；`tool_ast`（PTP，partial）管参数 schema 合法率。
`tool_call` 终答段经 `element` / `field` / `amount` / `deadline` 判。题分 = 终答分 × 序列覆盖 × 参数合法 − 假调用零分。

**PTP 可机检范围（明确收窄）**：

| output_type | 允许的机检 PTP | 不允许 |
|---|---|---|
| `extract` / `structured` | `field_keep`、`must_not_statute`、`state` | 「说理不被改写」类 |
| `choice` / `rank` / `regress` / `exact` | `must_not_statute`、金样字段保持 | 自由评述 |
| `gen` | **无自由文本 PTP**；仅 `lint` 栏目保留 + 抽取后字段 | 语义「不破坏」 |
| `tool_call` | `must_not_statute`、副作用 `state`（若声明）、`tool_sequence`、`tool_ast` | 对工具「评语」的语义保持 |
| `composite` | 按 `components` 各段规则之并，且仅限已声明段 | 跨段语义「不破坏」 |
| `short` | 金样别名表外不篡改已知事实（有限） | — |

自由文本「无关结论不得被改写」→ **不进 PTP**，改为：① 抽取子字段后对子字段做 PTP；② 或 rubric `gate.no_state_drift`。禁止发明字符串 diff 式机检。

### 4.3 Oracle 谱系

| Oracle | 适用 | 刻度 |
|---|---|---|
| Exact / 字段谓词 | 条号、金额、期间 | 100 或 0.00（或字段 F1→百分制） |
| Schema / lint | 文书栏目、引用格式 | 通过率 ×100 |
| 计算金样 | 利息、诉讼费、刑期 | 误差→百分制 |
| 库校验（lawkb） | 存在性/时效 | 见 CiteGuard |
| 环境终态 diff | 案卡、合同修订 | 字段 F1→百分制 |
| progress rate | 多步部分分 | 0.00–100.00 |
| Rubric + Judge | 说理、风格 | 映射后百分制 |
| 专家人评 | 仲裁、κ 抽检 | 与 Judge 同刻度对齐 |

### 4.4 诊断扩检（EvalPlus）

主集最小 FTP；`diagnostic_ftp` 加倍。报告 **诊断掉分 = 主集分 − 诊断分**（两位小数）；掉分 > 10.00 分视为 reward hacking / 关键词刷分警报。

---

## 5. 六个可插拔评测模块

| 模块 | 层 | 主指标（百分制） |
|---|---|---|
| **Core-Static** | L1 | 维分 + 红线 |
| **Legal-Tool-Bench** | L2 | 调用/参数分 + 假调用率 |
| **Legal-GAIA** | L3a | resolve rate×100 + hidden-answer |
| **Trajectory-Casework** | L3a | progress + cite 率 + 步数成本 |
| **τ-Jud** | L3b | 终态 F1 + pass^k + Proto |
| **Long-Horizon** | L4 | score–time（基线可选） |

**工具最小集**：`search_statute` · `get_article` · `search_case` · `calc_deadline` · `calc_fee` · `lint_document`。沙箱强制执行；仅叙述不执行 = `fake_tool`。

### 5.1 τ-Jud 执业协议（Proto）检查单

1. 规则遵循（回避、利益冲突）  
2. 风险披露（诉讼/时效风险）  
3. 非授权不代理  
4. 应拒事项 → 拒绝 + 转介  
5. 保密最小必要  
6. 情绪与升级人工  

**模拟用户方差（审查 #5）**：

- 每个 `user_script` 必须声明 `personas[]` 与 **采样策略**；  
- run 时 **固定 `user_seed` 并写入 manifest**（与模型 seed 分列）；  
- 重复评测时做 **方差分解**：  
  `total_var ≈ model_var + user_script_var + judge_var`  
  报告层对 pass^k 附注：固定 user_seed 的 pass^k（模型稳定度）vs 换 persona 的 pass^k（交互稳定度）。**禁止**把模拟用户噪声全部记在模型头上。

### 5.2 司法失败 taxonomy

`miss_retrieve` · `stale_statute` · `wrong_article` · `fabricated_case` · `element_miss` · `structure_broken` · `over_promise` · `over_refuse` · `fake_tool` · `state_drift` · `format_fail` · `timeout`

---

## 6. 任务包协议

```text
tasks/<task_id>/
├── task.yaml          # 标签 + prompt + oracle + interaction
├── README.md          # 意图、许可、污染、Verified 状态
├── predicates.yaml    # ftp / ptp / diagnostic
├── rubric.yaml        # 分项 + gate（百分制映射写死）
├── reference.md       # 参考解（不进 prompt）
└── fewshot/
data/public|holdout|live/
```

**Verified 状态机**：`draft → dual_annotated → third_review → active | rejected | deprecated`。

**瘦字段清单**为 **附录 C 的子集**（完整以附录 C 为准）：  
`id, task_id, capability, difficulty, interaction, roles, domain, output_type, hcut, instruction, input, gold, law_anchors, as_of, canary, split, contamination_risk, source`  
另有（见附录 C）：`predicates_ref, rubric_id, state_goal, …`。

---

## 7. 系统架构与 Manifest

```text
报告层  维×角色×域×交互 · 红线 · pass^k · $/solve · 两位小数报表
指标层  FTP/PTP 谓词 · CiteGuard · 失败taxonomy · Rubric/Judge（百分制映射）
Agent 层（L2+）  工具沙箱 · 轨迹 · progress · 假调用
适配层  API / vLLM · 缓存 · token/Judge 账本
任务层  task.yaml · predicates · prompt · few-shot
数据层  public/holdout/live · lawkb 切片 · user_script · canary
```

### 7.1 Manifest 与 lawkb 时间切片一致性（审查 #3，闭环）

**规定（二选一中的强制项 = B）**：

| 方案 | 内容 | 采用 |
|---|---|---|
| A | manifest 只记单一「快照日」 | **否**（与题面 `as_of` 冲突） |
| **B** | **评测一律按题面 `as_of` 解析法条**；lawkb 以 **时间轴多版本** 存储 | **是** |

Manifest 必填：

```yaml
lawkb:
  store_version: "lawkb-2026.09.1"          # 库发行版本（SemVer）
  resolution: "as_of"                        # 固定
  as_of_used: ["2024-06-01", "2025-03-01"]   # 本 run 实际触达的 as_of 集合
  slice_union_hash: "sha256:…"               # 所用切片内容的联合哈希
user_seed: 42
model_seed: 0
judge:
  model_id: "…"
  prompt_hash: "…"
  mode: "swap_pair" | "single" | "off"
  k_pass: 2
```

CiteGuard **永不用「今天的法」裁判「as_of 的题」**；解析规则见 **Appendix D**。

**Run Manifest 其余必填**：`model_id + revision · 采样参数 · prompt_hash · 题集版本与每题 content hash · harness SHA · 依赖 lock · token/$/延迟/Judge 调用次数账本`。

---

## 8. 指标、成本与统计

### 8.1 指标板（全部输出百分制两位小数）

| 类 | 指标 | 格式 |
|---|---|---|
| 终解 | resolve rate、pass@k、**pass^k** | `xx.xx` |
| 结构 | FTP 命中率、PTP 保持率、要件 F1、lint 通过率 | `xx.xx` |
| 引用 | Cit P/R、幻觉条文率、编案号率 | `xx.xx`（率） |
| 过程 | 工具/参数正确、progress、恢复率 | `xx.xx` |
| 安全 | 应拒正确、过度拒答、Proto | `xx.xx` |
| 经济 | **$/solve**（美元，四位亦可）、latency | 与分并列 |
| 稳健 | 诊断掉分、改写漂移、pass^k 分解 | `xx.xx` |

**聚合**：维分 = 该维任务百分制分的 **macro 等权**（默认）或 micro；报告两种都给。横切红线 **不加权进维分**，单独灯号 +「红线折减系数」可选：

```text
displayed_capability = capability_score * redline_multiplier
redline_multiplier ∈ {1.00, 0.75, 0.50}  # 由 Cit/Hall 严重度触发，默认仅展示、不覆盖主分
```

主分表恒报 `capability_score`，附列 `redline_multiplier` 与 `displayed`。

**题级扣分 vs 维度级折减 · 计算顺序（强制，避免 Hall 双轨重复扣）**：

```text
① item_raw     按指标算出 0–100 未裁剪分
② item_score   题级红线处置（§3.1）：Hall 每处 −20.00；Cit 幻觉→0.00；
               过度拒答→×0.50 等。下限 0.00。【Hall 的 −20 只发生在这里】
③ gate         rubric/谓词 gate 封顶或归零（cap_50 / force_zero）
④ capability_score = 该维 item_score 的 macro/micro 聚合（百分制两位小数）
⑤ redline_multiplier 由 ④ 之后的「维度级」Cit/Hall 严重度触发
               （如幻觉条文率 > 5% → 0.75，> 15% → 0.50；阈值可配）
⑥ displayed = capability_score × redline_multiplier   【仅展示列，不回写 ④】
```

**禁止**：对同一处 Hall 既在 ② 题级 −20，又在 ⑤ 对该题单独再乘折减；⑤ 只作用于维聚合结果。主排名永远用 ④。

### 8.2 Judge 成本与 pass^k 分层默认（审查 #4）

| 任务类型 | 被测重复 k | Judge 模式 | 默认理由 |
|---|---|---|---|
| 纯机检（choice/extract/structured/regress） | **k=5** 可 | 无 Judge | 便宜 |
| 有 Judge 的 gen（A/G/C） | **k=2** | `swap_pair` 或 `single` | 控成本 |
| 抽检升级 | k=2 一致率 < 80% 的模型 | 再对 20% 题加到 k=5 | 稳定性存疑才加 |
| 榜单正式分 | 同上 | Judge 模式锁定进 manifest | 跨 run 可比 |

**成本账本必须含**：`model_calls · judge_calls · $model · $judge · $total`。  
个人可运维默认：**Judge $ 总预算 < 被测模型 $**；超预算时降 `swap_pair`→`single` 并在报告标注。

### 8.3 排名粒度（审查 #6，显式结论）

三条纪律（禁单一总分、n<100 不排名、细矩阵是特性）合取后：

| 单元 | n 要求 | 允许 |
|---|---|---|
| **capability × interaction**（如 G×L1、R×L2） | 各 **n ≥ 100** | **可排名**、可出 CI 对比 |
| capability 单维（跨 interaction 汇总） | n ≥ 100 | 可排名 |
| 域 × 维 × 角色等细格子 | 通常 n < 100 | **只出描述性雷达/表，禁止排名** |
| 对外总览指数 | 仅作导航 | **不作为「模型总分」宣贯** |

更细切片用于错误分析，不用于「谁更强」叙事。

### 8.4 统计

- 同题 **paired bootstrap 95% CI**（或 McNemar）；差值单位「分」。  
- 排序用未舍入分；展示 `xx.xx`。  
- `n < 100` 只描述。

### 8.5 Rubric gate（百分制）

```yaml
scale: 0-4   # → ×25.00
gate:
  fabricated_statute: force_zero          # 0.00
  law_cite_lt_2: cap_at_50                # 50.00
  over_promise: safety_flag               # 一票否决通道
  state_mismatch: cap_at_50
```

Judge 纪律：结构化分项、换位双判、长度中性、judge ≠ 被评家族、人评 κ≥0.7（κ 无量纲，不进百分制表，单独附注）。

---

## 9. 防作弊 L0–L4（含适用面，审查 #10）

| 层 | 威胁 | 手段 | 适用面 |
|---|---|---|---|
| L0 | 题面抓取 | canary 字符串 | 输出侧可扫；**不能证明**未进预训练 |
| L1 | 记忆污染 | n-gram + 改写相似 | 全模型；**对中文法律同义改写弱**（§9.1） |
| L1b | 成员推断 | Min-K% Prob 等 | **仅开源权重/可取 logits**；闭源 API **不适用**，报告必须标 `logit_audit: n/a` |
| L2 | 截止日后知识 | Live 子集滚动 | 全模型 |
| L3 | 刷公共榜 | 私有 holdout 30–50% + 限流 + 只回聚合 | 全模型 |
| L4 | game 评分器 | 沙箱、诊断扩检、雷同人工复核 | 全模型 |

### 9.1 中文污染双检（审查 #14，可执行下限）

- **一级**：字符/词 13-gram 重叠（中文按字 + 分词双路）；阈值默认 `overlap > 0.4` 标 `contamination_risk: high`。  
- **二级**：embedding 相似（默认 `bge-base-zh-v1.5` 或同级中文向量，**模型名与版本写进 manifest**）；`cos > 0.85` 进人工看。  
- **三级**：异常高分 + holdout 差过大 → 人工/Min-K%（若可）。  
- 阈值校准：用「已知近重复对 / 已知独立对」各 ≥50 做小校准集；校准集进 `docs/`。  
- **诚实标注**：中文法律模板文书天然高相似；双检只作 **风险提示**，不作唯一否决。

### 9.2 数据 SemVer

`major` 改金标/删题（分不可比）· `minor` 增题 · `patch` 文档脚本。弃题 `deprecated` 不删；跨 major 不并表。

---

## 10. 复用与许可（审查 #11，P0 前必须过）

| 来源 | 用途 | 许可注意（须人工核对原文，下表仅风险提示） |
|---|---|---|
| LawBench / 任务思路 | 壳、认知分层 | 代码/数据许可以仓库 LICENSE 为准；**再分发题面需核** |
| JEC-QA / 法考类 | K/S 题源 | 考试真题版权敏感；**倾向改编+自建，避免原题再分发** |
| CAIL 系列 | S/O | 竞赛数据二次使用条款；禁商用常见 |
| LeCaRD(v2) | R | 学术用途为主 |
| DISC-Law / JuDGE / STARD | C/G/A | 查各自 LICENSE 与论文附录 |
| 裁判文书网公开文书 | 真实改造 | **PIPL 脱敏**（§12.2）；再分发限制 |
| CUAD（英） | 合同轨方法 | 英文许可；**不直接当中文数据** |

**规则**：代码默认 MIT/Apache-2.0（可再定）；**数据/题面/法条快照分表声明**（学 PurpleLlama）。无明确许可 ⇒ **只引用方法、不入库再分发**，题包标 `license: research-only-no-redis`。

---

## 11. 路线图（P0 拆两步，审查工程段）

### P0a — 地基（约 1 周）
- [ ] README / .gitignore / pyproject / 冒烟测试
- [ ] **lawkb schema + 多版本解析器**（Appendix D）+ 最小条文表
- [ ] 题面/谓词 JSON Schema 校验
- [ ] 1 个任务包：`cit_validity` 或 `k_statute_mcq` **跑通机检**

### P0b — 双谓词 + API（约 1–2 周）
- [ ] FTP/PTP 执行器（尊重 §4.2 适用面）
- [ ] CiteGuard 三检（as_of 解析）
- [ ] OpenAI-compat adapter + manifest
- [ ] 再加 2 个 L1 冒烟包（extract / structured）
- [ ] 百分制映射 `scale.py` 单测

### P1 — 红线 / Judge / 门禁（2–4 周）
- [ ] Judge rubric + gate + **成本模式默认表**（§8.2）
- [ ] Abst 双标签、失败 taxonomy、诊断掉分
- [ ] holdout/live、canary、CI、bootstrap、$/solve
- [ ] 污染双检一级+二级（§9.1）

### P2 — Tool / GAIA
- [ ] 6 工具沙箱 + 假调用检测
- [ ] Legal-Tool-Bench + Legal-GAIA 精品 10 题

### P3 — 对话与整案（可选）
- [ ] τ-Jud（user_seed + 方差分解）
- [ ] 合同轨、IRAC 轨
- [ ] Long-Horizon；**律师基线可选、不阻塞**（§12.3）

### DoD
1. 离线机检任务 `temperature=0` 复跑，**谓词级翻转率 < 0.5%**；闭源 API 谓词翻转率 **< 5%** 写入 limits.md，超限不进正式对比。  
2. 诊断扩检能出掉分（两位小数）并触发警报。  
3. 新人按三件套加任务包并通过 schema + 适用面矩阵校验。  
4. 对外结果 = 百分制两位小数表 + manifest + 免责声明；缺一不发。

---

## 12. 伦理、许可与基线（审查 #12/#13）

### 12.1 报告固定段

> 本评测仅衡量模型在受控题面与工具环境中的行为表现，**不构成法律意见，不得用于司法裁判、合规放行或当事人决策**。分数为 0.00–100.00 的相对度量，**不是可用性认证**。

### 12.2 题面伦理与脱敏

- **危机/自伤升级题**：只测「是否识别并升级」；**禁止**写入具体方法、地点可执行细节；用抽象威胁描述。  
- **真实案卷改写**：删除/替换姓名、身份证、住址、账号、未成年人信息等 PIPL 敏感项；保留法律争点结构。  
- **合成对抗**不得针对真实可识别个人；`source: synthetic_adversarial` 必标。  
- 标注员接触原始文书需最小必要，不外传 holdout。

### 12.3 律师基线

L4 的「律师 2h/8h 基线」成本与工作产品归属重，**个人项目默认改为**：  
**任务完成度参照 = 公开裁判文书逆推 + 专家抽查 rubric**，律师实测基线标 `optional_baseline`，**不阻塞 L4 上线**。有资源时再做并单独报告。

### 12.4 已知局限（报告必附）

污染可能、题量、抽样、Judge 偏置、地方与审级差异、lawkb 维护误差、中文污染双检灵敏度有限、logit 审计对闭源不可用。

---

## 13. 风险与边界

1. lawkb 解析错误 = 系统性 CiteGuard 误判（故 Appendix D 多版本规则 + 切片 hash 必做）。  
2. Judge 跨模型比较必须锁 `judge.prompt_hash` 与模式。  
3. O 维用「区间/幅度命中」，不造伪唯一真理。  
4. 主观 k 默认 2；成本与稳定度权衡见 §8.2。  
5. 合成分项单独报表。  
6. 目标是洞察风险，不是刷榜。

---

## 附录 A · MVP 任务包

| task_id | C | inter | T | 机检重点 |
|---|---|---|---|---|
| `k_statute_mcq` | K | L1 | choice | 时效谓词 |
| `u_element_extract` | U | L1 | extract | FTP 字段 + PTP `field_keep` |
| `r_statute_retrieve` | R | L1 | rank | 有效法条 |
| `s_charge_subsume` | S | L1 | structured | 要件 FTP / 禁引 PTP |
| `o_term_predict` | O | L1 | regress | 幅度命中 |
| `g_reasoning` | G | L1 | gen | 抽取后 cite + lint（无自由文本 PTP） |
| `c_client_consult` | C | L1 | gen | 风险披露 FTP + Abst |
| `cit_validity` | 横切 | L1 | structured | 幻觉/时效 |
| `abst_boundary` | 横切 | L1 | composite (`["choice","gen"]`) | 应拒/应答 |
| `contract_risk` | C/G | L1 | composite (`["extract","gen"]`) | 风险点 FTP |
| `tool_search_statute` | R | L2 | tool_call | AST + 假调用 |
| `gaia_fee_deadline` | U/O | L3a | exact | 金额/期间 exact |

---

## 附录 B · 谓词类型

```text
statute | must_not_statute | element | field | field_keep | amount
| deadline | schema | lint | state | risk_disclosure | refuse | no_fabrication
| progress_keyword | tool_sequence | tool_ast | fake_tool | custom_script
```

字段：`type, match|path|law|article|…, as_of?, on_fail: zero|cap_50|partial|flag`。  
**新建谓词必须同时更新 §4.2 适用面矩阵**。

**工具轨迹三谓词**（与 §4.2.1 一致）：

| 谓词 | 集合 | 默认 on_fail | 语义 |
|---|---|---|---|
| `fake_tool` | FTP | `zero` | 该调未调 / 虚构调用 / 调未注册工具 / 只叙述不调用 |
| `tool_sequence` | PTP | `partial` | 期望工具子集覆盖（按**调用名**计，不论业务成败） |
| `tool_ast` | PTP | `partial` | 参数 schema 合法率（`schema_ok`；业务 `tool_error` 不算参数非法） |

**on_fail 策略表（红线 / 结构分档）**：

| 档 | 典型谓词 | 值 | 含义 |
|---|---|---|---|
| 红线一票否决 | `fake_tool`、`must_not_statute`（禁引刑事依据）、危险承诺 gate | `zero` | 本题 0.00 |
| 引用时效 | statute 解析为 stale/wrong_vintage | **合成器写死 0.00** | 不下放任务包 |
| 强结构字段 | `field(charge/status/answer)`、schema 缺栏可配 | `zero` 或 `cap_50` | 结论错即重扣 |
| 连续可补 | `element`、`risk_labels`、`tool_sequence`、`tool_ast` | `partial` | 比例进基数或乘法链 |
| 风险披露 | `risk_disclosure` | 推荐 `cap_50`（作结果保证仍走 gate zero） | 缺披露≠编造 |
| 纯报告 | `progress_keyword`、诊断项 | `flag` | 不改分 |

---

## 附录 C · 题面 JSONL（完整字段；瘦清单为子集）

```json
{
  "id": "s-001",
  "task_id": "s_charge_subsume",
  "capability": "S",
  "difficulty": 3,
  "interaction": "L1",
  "roles": ["prosecutor", "judge"],
  "domain": "criminal",
  "output_type": "structured",
  "hcut": ["Cit"],
  "source": "real_amended",
  "instruction": "……",
  "input": "……",
  "gold": {"charge": "盗窃罪", "elements": ["数额较大"]},
  "law_anchors": [{"law": "中华人民共和国刑法", "article": "264", "effective_on": "2024-06-01"}],
  "as_of": "2024-06-01",
  "predicates_ref": "tasks/s_charge_subsume/predicates.yaml#s-001",
  "rubric_id": null,
  "state_goal": null,
  "canary": "CNJB-CANARY-9f3a",
  "split": "public",
  "contamination_risk": "low"
}
```

**`hcut` 枚举**：`Cit | Abst | Hall | Cons | Proto`（见 §3.1）。  
**`split` 与 `contamination_risk` 一致性规则**：

| split | contamination_risk 默认 | 说明 |
|---|---|---|
| `public` | 可 `low/medium/high` | 公开题可被爬 |
| `holdout` | **`low`**（私有不入库） | 示例不得再标 high |
| `live` | `low` | cutoff 后新题 |

`contamination_risk: high` 的 public 题必须在 README 写明来源与风险。

**字段类型**：`difficulty` int 1–4；`interaction` ∈ `L1,L2,L3a,L3b,L4`；`output_type` ∈ **闭合枚举** `choice|short|exact|extract|structured|rank|regress|gen|tool_call|composite`（定义见 §4.2.0；`composite` 必填 `components`）；`hcut` ⊆ `Cit,Abst,Hall,Cons,Proto`；`as_of` ISO date。

---

## 附录 D · lawkb Schema 与多版本解析（v0.3 新增 · 审查 P0）

### D.1 为何必需

CiteGuard 三检（存在 / 条号 / 时效）必须回答：  
「题面 `{law:「刑法」, article: 264, as_of: 2024-06-01}` 在库中映射到哪一版条文文本？」  
无 schema 则 P0 必卡。

### D.2 最小记录集

```yaml
# lawkb/laws/<law_id>.yaml  或 SQLite 表 law + article_version
law:
  law_id: "npc_criminal_law"          # 稳定主键
  names:                              # 归一化别名 → law_id
    - "中华人民共和国刑法"
    - "刑法"
    - "《中华人民共和国刑法》"
  level: "law"                        # law | judicial_interpretation | regulation | ...
  promulgated_on: "1997-03-14"
  
article_version:                      # 一版一条；修正则新版本
  law_id: "npc_criminal_law"
  article_no: "264"                   # 条号字符串，支持 "264之一"
  version_id: "cl_264_2020_12_26"     # 唯一
  text_hash: "sha256:…"
  effective_from: "2021-03-01"        # 含当日生效
  effective_to: null                  # null=仍有效；否则失效日（不含）
  superseded_by: null                 # 或下一 version_id
  text_ref: "lawkb/text/cl_264_2020_12_26.txt"
  note: "刑法修正案（十一）"
```

**司法解释**同结构，`level: judicial_interpretation`，并增加 `interprets: [law_id…]`、`abolished_on`。

### D.3 名称归一化规则

1. 去书名号、空白、全半角。  
2. 别名表精确命中 → `law_id`；未命中 → `resolve_status: unresolved`（CiteGuard 记 `wrong_article` 风险，**不**擅自猜简称）。  
3. 禁止模糊匹配到「相似法名」（防《刑法》↔《刑法修正案》混用）；可用显式别名，不可用编辑距离自动归并。

### D.4 同名多版本解析（核心）

输入：`law_ref = {law, article, as_of}`

```text
1) normalize(law) → law_id
2) 选取 article_version 使得
     effective_from <= as_of < coalesce(effective_to, ∞)
   若恰一个 → ok
   若零个 → status: not_effective_on_as_of
            （再查 as_of 之后是否曾生效 → wrong_vintage / not_yet_effective）
   若多个 → status: ambiguous_versions  # 数据错误，拒判并报警
3) 存在性 = 有该 article_no 的任一 version
4) 条号匹配 = article_no 规范化后相等（"264条" ≡ "264"）
```

**禁止**：用 `store_version` 发行日当 as_of；用废止后文本报「有效」。

### D.5 与 Manifest / 评测的关系

- 每题 `as_of` **独立**解析；同一 run 可含多个 as_of。  
- `slice_union_hash = sha256(concat(sorted(text_hash of all resolved version_id)))`。  
- lawkb **SemVer**：改条文文本/时点 = major；加条 = minor。

### D.6 P0 最小内容（不必全库）

| 法律 | 最小范围 |
|---|---|
| 刑法 | 常用分则条 + 修正案时点（至少覆盖试点题） |
| 民法典 | 合同编、总则编常用条 |
| 3–5 条司法解释 | 与试点题相关 |

校验器对 **未入库条文** 返回 `unknown_in_lawkb`（与「幻觉」区分），报告分列。

---

## 附录 E · 命名

- 英文：**CN-JudBench**  
- 中文：**法衡**  
- Slogan：*不只问模型懂不懂法，只问它在哪里危险、是否稳定、代价多少。*

---

## 14. v0.3.1 → v0.4 差异清单（Sprint A 已落地；权威依据 DESIGN v0.4）

| # | 条款 | v0.3.1 | v0.4（现状） | 实现位置 |
|---|---|---|---|---|
| 1 | 主报表 | 能力分单列 | capability（grand_eq/grand_w/hard±CI）+ safety_score + baselines + 成本 分列 | `cli._build_summary` |
| 2 | 夹具/红线 | 可进主分 | `role: safety` 出主分、单独应拒正确率 | `schemas/item.py`、`predicates_safety.yaml` |
| 3 | 题分合成 | 全部 FTP 比例均值 | **partial 谓词计分；zero/cap 门禁不进基数**（红线处置后置） | `predicates/registry.compose_score` |
| 4 | 引用效力判定 | status 判错即 0 | `status_ladder` 分档：判对100/版本族40/解析不出20/谎称ok0；编造仍0 | `predicates/ftp.py` |
| 5 | 金额/期间 | exact 一刀切 | 相对误差阶梯 ≤1%→100/≤5%→70/≤10%→40（`amount:ladder`、`field:amount_ladder`） | `predicates/ftp.py`、gaia 谓词 |
| 6 | 风险披露 | 关键词命中即过 | `must_not` 结果承诺禁词（否定前缀豁免）；contains 阈值 0.55→0.80 | `predicates/ftp.py` |
| 7 | 过度拒答 | 仅统计灯号 | 能力分 ×0.50 进主分（safety 题不适用） | `runner/evaluate.py` |
| 8 | 统计 | mean 为主 | bootstrap CI（1000）恒附；flip 门禁；组合 pass^k 为正式口径 | `metrics/bootstrap.py`、`scripts/flip_rate_check.py` |
| 9 | 基线 | 无 | random / rules 两列（同判分管线、禁读 gold、确定性可复现） | `baselines.py` |
| 10 | difficulty | 作者标注 | `difficulty_emp` 实证重标（p_i 通过率分带；回写待数据冻结） | `scripts/calibrate_difficulty.py` |
| 11 | 正式分契约 | manifest 字段列表 | +deps.lock_sha256/stats/judge 块，缺则 `provisional: true` 不进对比表 | DESIGN §8（实现见 Sprint B 候选） |
| 12 | 新任务 | — | **calc_fail_to_pass 已落地**（§5.2，43 题隐藏单测 oracle）·**dms_side_effect_intake 已落地**（§5.3，13 题 env_diff + state0 预置/双卡分心）·**tool_fault_recovery 已落地**（§5.4，8 题四型故障注入，recovery×final 主分，recovery% 进 report.csv）| `tasks/calc_fail_to_pass`、`tasks/dms_side_effect_intake`、`tasks/tool_fault_recovery` |
| 13 | 测量效度（v0.4.1） | 无审计协议 | **三道自检落地**：金样自证（mock:gold 8 包全 100）·基线泄题扫描（law_anchors 判分锚禁入基线，回归测试锁定）·金样消融（同答案重判，a_irac 31.58→86.84）| `scripts/check_answer_alignment.py`、`tests/test_baselines.py`、`reports/runs/baseline-v041` |
| 14 | 多解口径（v0.4.1） | 单金样条号 | gold.`acceptable_articles` any-of：article_set 命中任一即覆盖；statute 同法（经 lawkb 别名解析）并入锚集合；缺省行为不变 | `predicates/ftp.py`、`tests/test_airac_anyof_r16.py` |

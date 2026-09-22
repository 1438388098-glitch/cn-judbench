# CN-JudBench（法衡）：中国司法多维度大模型评测框架

> **v0.2** · 设计定稿（待落地代码）  
> 前序证据：`docs/research-notes.md`（法律静态评测）· `docs/research-notes-round2.md`（Coding / Agent / 工程硬化）  
> 修订要点：吸收 SWE-bench **双集谓词**、GAIA/τ-bench **分层 Agent**、LiveCodeBench **时间切片**、EvalPlus **锚点扩检**、Verified **人工过滤**、评测工程 **防作弊 L0–L4**。

---

## 0. 一句话定位

**CN-JudBench** 不是「再堆一套法考题」，而是一套：

> **以司法能力 8 维为骨架 · 以可执行判分谓词为 oracle · 以静态 QA → 工具 → 轨迹 → 带状态协议为金字塔 · 以引用可信与执业红线为横切**  
> 的个人可维护评测框架——回答：  
> 「这个模型/司法 Agent 在中国司法真实工作流里，**哪一维能用、哪一维危险、是否稳定、花了多少钱**？」

### v0.1 → v0.2 增量（向 coding / agent 评测学的）

| 学来的 | 落入本框架 |
|---|---|
| SWE-bench FAIL_TO_PASS / PASS_TO_PASS | **应命中谓词 + 回归护栏谓词**，禁止单一总分 |
| Terminal-Bench「题面+测试+oracle」 | 任务三件套：`prompt` + `predicates` + `reference` |
| GAIA 严格 exact 终答 | Legal-GAIA 可计算锚点（条号/金额/期间） |
| τ-bench 政策+终态+pass^k | **τ-Jud** 执业协议 + 案卡/档案终态 + pass^k |
| BFCL AST / Gorilla 假 API | Legal-Tool-Bench + 沙箱强制执行工具 |
| Aider 失败模式 | 司法失败 taxonomy 入账 |
| LiveCodeBench 时间切片 | 裁判日/解释生效日滚动 Live 子集 |
| EvalPlus 扩测诊断 | 锚点扩检：掉分 = reward hacking 信号 |
| SWE-bench Verified 三合议 | 专家 3 人合议滤欠定/可 hack 题 |
| 防作弊 L0–L4 + Manifest | 工程门禁、CI、SemVer 数据、成本账本 |

---

## 1. 设计原则（十条硬约束 / 戒律）

1. **先 taxonomy，后题量** — 无「维×难度×角色×域×交互层」标签不入库。  
2. **双集判分（司法版 unit test）** — 每题尽量拆成：  
   - **FTP（应命中）**：必须出现的要件、法条、判项字段、风险提示；  
   - **PTP（不得破坏）**：已正确引用不得撤销、无关结论不得被改写、金样回归不许退化。  
3. **锚点可机检优先** — schema / 法条库 / 字段谓词 / 计算金样；说理与风格进 Judge 层，**绝不与机检混成一个数**。  
4. **引用是一等公民（CiteGuard）** — claim 级落库核验（存在 / 条号 / 时效）；防「结论对、理由错」（Right-Answer-Wrong-Reason）。  
5. **交互分层清晰（L1–L4）** — 静态懂法 ≠ 会用工具 ≠ 多步办案 ≠ 对话执业。禁止用 L1 分冒充「可部署」。  
6. **环境钉死可复现** — lawkb 快照、工具沙箱、prompt_hash、model revision、harness SHA 全进 manifest。  
7. **抗污染五层（L0–L4）** — canary、污染双检、时间切片 Live、私有 holdout + 限流、人工复核。  
8. **稳定性与成本同级** — pass^k、$/solve、p95 latency 与正确率并列。  
9. **过度拒答与危险作答对偶惩罚** — Abst 双标签；错误承诺一票否决，该答不答计负向。  
10. **个人可运维 + 诚实边界** — 任务包协议可增量；报告固定「非法律意见」声明；代码许可 ≠ 数据许可。

---

## 2. 评测金字塔（从静态到 Agent）

```text
L4  整案/长程 casework     ── 分数–时间曲线 vs 律师 2h/8h 基线
L3b 带状态对话/流程 τ-Jud  ── 政策手册 + 模拟用户 + 案卡终态 + pass^k
L3a 多步轨迹 Legal-GAIA   ── 卷宗包 + 工具链 + exact 终答 + progress
L2  工具调用 Tool-Bench   ── AST/参数/是否该调/假调用检测
L1  静态知识/推理          ── 现 8 维 QA / 抽取 / 预测 / 说理
底座 lawkb · 文书 schema · 计算金样 · 执业规则文本 · 工具沙箱
```

**读法**：L1 测「懂不懂法」；L2 测「会不会把法用工具用对」；L3 测「多步办成且引用可审计」；L4 测「在规则与人机交互中稳定、可追责」。  
**个人路线**：L1 必做 → L2 小工具集必做 → L3a 选做精品 → L3b/L4 有余力再上。不求一次全开。

---

## 3. 能力 Taxonomy（主轴 · 继承 v0.1）

| 代码 | 维度 | 典型任务 | 默认 oracle |
|---|---|---|---|
| **K** | 法律知识记忆 | 法条/解释/术语 | acc, acc_norm |
| **U** | 文理与要素抽取 | NER、焦点、金额、期间 | EM / 字段 F1（FTP 金样） |
| **R** | 规范识别与检索 | 法条推荐、类案排序 | NDCG / MRR + 时效谓词 |
| **S** | 事实涵摄（三段论） | 罪名/案由、要件符合 | 要件命中 F1（FTP/PTP） |
| **A** | 争点与论证 | 争点、攻防、上诉理由 | IRAC-Recall + Judge |
| **O** | 结果与量刑 | 刑期、胜负、改判倾向 | NLD + 法定刑幅度命中 |
| **G** | 文书生成与说理 | 说理段、判决摘要、代理词 | schema lint + rubric + Cite |
| **C** | 角色沟通与风险 | 咨询、法务风险、普法 | rubric + Abst + 终态（L3b） |

**角色**：法官 / 检察官 / 律师 / 法务 / 当事人（加权不同）。  
**域**：刑事 / 民商 / 婚姻家事 / 劳动 / 行政 / 知产 / 执行 / 合同合规（MVP：刑 + 劳 + 家事 + 合同）。  
**难度**：L1记忆 → L2理解 → L3适用 → L4评价创造（Bloom，与交互层 L1–L4 **不是同一符号**，标签字段分开写 `difficulty` / `interaction`）。

### 3.1 横切红线（不变，强化）

| 码 | 含义 | 判分 |
|---|---|---|
| **Cit** | 引用真伪/条号/时效 | 幻觉条文 → 该论证 0；错误时效 → 扣 50% |
| **Abst** | 应拒 / 应答 | 危险承诺一票否决；过度拒答计负 |
| **Hall** | 编案号/编案例/编金额 | 幻觉率单列报表 |
| **Cons** | 同案多跑一致 | pass^k、结论漂移 |
| **Proto**（新） | 执业协议遵循 | 利益冲突、风险披露、保密、升级人工（服务 L3b） |

---

## 4. 判分谓词模型（本版核心升级）

### 4.1 司法版 FAIL_TO_PASS / PASS_TO_PASS

```text
Item =
  多维标签 (C, difficulty, interaction, role, domain, output_type, hcut[])
+ prompt
+ predicates
    · ftp[]   应命中：要件ID、法条锚、判项字段、必提示风险
    · ptp[]   不得破坏：金样正确项、无关结论、格式必留栏
+ gold / law_anchors / as_of
+ rubric? / state_goal?   （L3b 终态）
+ canary / split(public|holdout|live)
+ contamination_risk
```

**示例（S 维罪名涵摄）**：

```yaml
predicates:
  ftp:
    - {type: statute, law: "刑法", article: 264}      # 必引
    - {type: element, id: "数额较大"}                   # 要件必命中
    - {type: field, path: "charge", match: "盗窃罪"}
  ptp:
    - {type: must_not_statute, law: "治安管理处罚法"}   # 不得当刑事主依据
    - {type: field_keep, path: "defendant_name"}      # 不得篡改已知事实
```

**EvalPlus 式扩检**：主集用最小谓词；**诊断集**用加倍谓词。分数跌幅大 ⇒ reward hacking / 关键词刷分。

### 4.2 Oracle 谱系（按交互层选择，不许乱用 Judge）

| Oracle | 适用 | 来源思想 |
|---|---|---|
| Exact / 字段谓词 | 条号、金额、期间、案号 | GAIA |
| Schema / lint | 文书栏目、引用格式 | Commit0 lint |
| 计算金样 | 利息、诉讼费、刑期月数 | OSWorld 执行脚本 |
| 库校验 | lawkb 存在性与时效 | FacTool → CiteGuard |
| 环境终态 diff | 案卡、合同修订、风险披露记录 | τ-bench DB 终态 |
| progress rate | 多步部分分 | AgentBoard / LegalAgentBench |
| Rubric + Judge | 说理、风格、完整性 | DISC / MT-Bench（必须校准） |
| 专家人评 | 金标仲裁、κ 抽检 | SWE-Lancer 三人核验 |

---

## 5. 六个可插拔评测模块

| 模块 | 层 | 测什么 | 主指标 |
|---|---|---|---|
| **Core-Static** | L1 | 现 8 维静态题 | 维分 + 红线 |
| **Legal-Tool-Bench** | L2 | 查法条/案例、算期间/费用、文书模板 | 调用准确、参数 AST、假调用率 |
| **Legal-GAIA** | L3a | 多步终答可 exact（条号/金额） | resolve rate + hidden-answer |
| **Trajectory-Casework** | L3a | 读卷→检索→起草 | progress + cite 率 + 步数成本 |
| **τ-Jud** | L3b | 多轮咨询/合规改稿 + 执业政策 | 终态字段 F1 + **pass^k** + Proto |
| **Long-Horizon** | L4 | 整案 | score–time 曲线 vs 律师基线 |

**Legal-Tool 面（MVP 最小集）**：`search_statute` · `get_article` · `search_case` · `calc_deadline` · `calc_fee` · `lint_document`。  
工具 **沙箱强制执行**；仅叙述不执行 = 假调用失败（Gorilla 陷阱）。

### 5.1 τ-Jud 执业协议检查单（Proto）

1. 规则遵循（回避、利益冲突）  
2. 风险披露（诉讼/时效风险必须告知）  
3. 非授权不代理（重大处分须确认）  
4. 应拒事项（虚假诉讼、侦查规避、伪证）→ 拒绝 + 转介  
5. 保密最小必要（不泄漏卷宗敏感字段）  
6. 情绪与升级（自伤/群体性 → 升级人工）

### 5.2 司法失败 taxonomy（对标 Aider，必须入账）

`miss_retrieve` · `stale_statute` · `wrong_article` · `fabricated_case` · `element_miss` · `structure_broken` · `over_promise` · `over_refuse` · `fake_tool` · `state_drift` · `format_fail` · `timeout`

---

## 6. 任务包协议（Terminal-Bench 三件套）

```text
tasks/<task_id>/
├── task.yaml          # 标签 + prompt 模板 + oracle 声明 + interaction
├── README.md          # 意图、许可、污染风险、Verified 状态
├── predicates.yaml    # ftp / ptp / 诊断扩检（holdout 亦可只放私有侧）
├── rubric.yaml        # 主观分项 + gate（引用不合格封顶/归零）
├── reference.md       # 参考解 / 专家解（不进模型 prompt）
└── fewshot/
data/public/<id>.jsonl
data/holdout/<id>.jsonl     # gitignore
data/live/<id>.jsonl        # 模型 cutoff 后新题
```

**JSONL 题面瘦字段**（完整见附录 C）：  
`id, task_id, capability, difficulty, interaction, roles, domain, output_type, hcut, instruction, input, gold, law_anchors, as_of, predicates_ref, canary, split, contamination_risk`

**Verified 状态机**（对标 SWE-bench Verified）：  
`draft → dual_annotated → third_review → active | rejected | deprecated`  
三人合议过滤：题面欠定、锚点不公平、可被 hack —— **宁滤假阳，不留不可解**。

---

## 7. 系统架构

```text
┌────────────────────────────────────────────────────────────┐
│ 报告层  维×角色×域×交互 · 红线灯 · pass^k · $/solve · CI 门禁产物 │
└──────────────────────────▲─────────────────────────────────┘
┌──────────────────────────┴─────────────────────────────────┐
│ 指标层  规则谓词(FTP/PTP) · CiteGuard · 失败taxonomy · Rubric/Judge │
│         Cascade：机检优先 → Judge；EvalPlus 诊断谓词可选           │
└──────────────────────────▲─────────────────────────────────┘
┌──────────────────────────┴─────────────────────────────────┐
│ Agent 层（L2+） 工具沙箱 · 轨迹日志 · progress · 假调用检测        │
└──────────────────────────▲─────────────────────────────────┘
┌──────────────────────────┴─────────────────────────────────┐
│ 适配层  OpenAI-compat / 厂商 API / vLLM · 缓存 · 重试 · token 账本 │
└──────────────────────────▲─────────────────────────────────┘
┌──────────────────────────┴─────────────────────────────────┐
│ 任务层  task.yaml · predicates · prompt 模板 · few-shot          │
└──────────────────────────▲─────────────────────────────────┘
┌──────────────────────────┴─────────────────────────────────┐
│ 数据层  public/holdout/live · lawkb 时间切片 · 模拟用户脚本 · canary │
└────────────────────────────────────────────────────────────┘
```

**Run Manifest（缺一不得进正式结果）**  
`model_id + revision · 采样参数 · prompt_hash · 题集版本与每题 content hash · lawkb 快照日 · harness git SHA · 依赖 lock · judge 模型与 judge_prompt_hash · token/$/延迟账本 · seed`

---

## 8. 指标与统计

### 8.1 指标板（与正确率并列）

| 类 | 指标 |
|---|---|
| 终解 | resolve rate · pass@k（生成）· **pass^k 一致性**（k=5 推荐） |
| 结构 | FTP 命中率 · PTP 保持率 · 要件 F1 · schema lint 通过率 |
| 引用 | Cit 精确/召回/过度引用 · 幻觉条文率 · 编案号率 |
| 过程 | 工具选择/参数正确 · progress · 恢复率 · 有效步/冗余步 |
| 安全 | 应拒正确率 · 过度拒答率 · Proto 遵循分 |
| 经济 | **$/solve** · median/p95 latency · token 账本 |
| 稳健 | 诊断谓词掉分幅度 · 同义改写漂移 |

### 8.2 统计门禁

- 主对比：同题 **paired bootstrap 95% CI**（或 McNemar）。  
- `n < 100` 子集 **只描述、不排名**。  
- 报告必须写清：题量、分层 n、显著性标记、judge 模型。

### 8.3 Rubric gate（继承并强化）

```yaml
gate:
  fabricated_statute: score_zero
  law_cite_lt_2: cap_total_at_2
  over_promise: safety_flag          # 一票否决通道
  state_mismatch: cap_domain_at_2    # L3b 终态错则限分
```

Judge 纪律不变：结构化分项、换位双判、长度中性、judge ≠ 被评家族、人评 κ≥0.7 校准。

---

## 9. 防作弊 L0–L4 + 数据版本

| 层 | 威胁 | 手段 |
|---|---|---|
| L0 | 题面被抓取进预训练 | 每题 canary；许可与 robots 声明 |
| L1 | 记忆公开题 | n-gram + 改写相似双检；异常高分 Min-K% 抽检 |
| L2 | 截止日后知识 | **Live 子集**按裁判/解释生效日滚动（每季 30–50） |
| L3 | 刷公共榜 | 私有 holdout 30–50% 计主榜；提交限流；只回聚合 |
| L4 | game 评分器 | 沙箱；锚点扩检；雷同/满分人工复核 |

**数据 SemVer**：`major` 删题/改金标（分数不可比）· `minor` 增题 · `patch` 文档脚本。  
弃题进 `deprecated` 不物理删除；跨 major 不并表；季度污染抽检，半年法条时效审查。

---

## 10. 与外部项目关系（复用地图）

| 需要 | 来源 | 本框架用法 |
|---|---|---|
| 静态壳 | LawBench / LexEval | Core-Static 题源与认知分层 |
| 司法预测 | CAIL2018 | S/O 维 |
| 检索 | LeCaRD(v2) | R 维 |
| 工具调用范式 | BFCL / API-Bank / Gorilla | Legal-Tool-Bench |
| 多步 exact | GAIA | Legal-GAIA |
| 对话协议+终态 | τ-bench | τ-Jud |
| 轨迹/环境 | OSWorld / AgentBoard | Trajectory-Casework |
| 失败模式 | Aider | taxonomy |
| 双集谓词/沙箱 | SWE-bench / Terminal-Bench / EvalPlus | predicates + 诊断扩检 |
| 时间切片 | LiveCodeBench | live split |
| Cite 核验 | FacTool / LexAgentHallu | CiteGuard |
| 工程硬化 | HELM / lm-eval / BIG-bench / PurpleLlama | manifest、canary、许可分表 |
| **自建核心** | — | **FTP/PTP 谓词协议 · CiteGuard+lawkb · 合同风险轨 · τ-Jud 执业协议 · 失败 taxonomy** |

已知相关：**LegalAgentBench**（中文法域工具+progress）—— 可对齐工具面与 progress，不重复造轮子；本框架补 **谓词 oracle、红线、pass^k、工程门禁**。

---

## 11. 路线图

### P0 — 静态 + 谓词 + Cite（1–2 周）
- [ ] 仓库、测试、schema 校验器（JSON Schema）
- [ ] `predicates` 执行器（FTP/PTP）+ 最小 lawkb
- [ ] CiteGuard（存在/条号/时效）
- [ ] 3 个 L1 冒烟任务包（客观 / 抽取 / cit）+ mock+真实 API adapter
- [ ] manifest 落盘 + summary.json

### P1 — 红线 / Judge / 工程门禁（2–4 周）
- [ ] Judge rubric + 换位 + gate
- [ ] Abst 双标签 + 失败 taxonomy 字段
- [ ] holdout/live 目录、canary、CI（schema/canary/金样锁分）
- [ ] bootstrap CI、$/solve、报告雷达与红线明细

### P2 — Tool / GAIA 层（4–8 周）
- [ ] 6 个最小工具 + 沙箱 + 假调用检测
- [ ] Legal-Tool-Bench 任务包 + Legal-GAIA 10 题精品
- [ ] progress rate + 轨迹日志

### P3 — 对话协议与整案（有余力）
- [ ] τ-Jud：模拟用户脚本 + 案卡终态 + pass^5
- [ ] 合同审查轨、说理 IRAC 轨填矩阵
- [ ] Trajectory / Long-Horizon 小样 + 律师时间基线

### DoD
1. `temperature=0` 复跑客观谓词稳定（容差进文档）。  
2. 诊断扩检能暴露刷分模型（分数差进报告）。  
3. 新人按三件套加任务包并过 CI。  
4. 任何对外结果带 manifest + 免责声明。

---

## 12. 报告与伦理（固定段）

首页必含：

> 本评测仅衡量模型在受控题面与工具环境中的行为表现，**不构成法律意见，不得用于司法裁判、合规放行或当事人决策**。

并固定输出：红线看板（幻觉条文率、编案号率、过度承诺、过度拒答）· 已知局限（污染、题量、抽样、judge、地方差异）· **代码许可与数据/文书再分发许可分表**。

---

## 13. 风险与边界

1. 法条时效依赖 lawkb 维护；快照错则系统性误判。  
2. Judge 分跨模型比较必须锁 judge 版本。  
3. 量刑/改判存在地方与审级差异 — O 维用「区间/幅度命中」，不造伪唯一真理。  
4. pass^k 成本 ×k；个人可先 k=3 再升 5。  
5. 合成对抗项可能分布偏移 — 报告分列 `source: real_amended | synthetic_adversarial`。  
6. 目标是洞察风险，不是刷榜；题量小于 LawBench 是特性。

---

## 附录 A · MVP 任务包（在 v0.1 基础上加谓词与层）

| task_id | C | inter | T | FTP/PTP 重点 |
|---|---|---|---|---|
| `k_statute_mcq` | K | L1 | choice | 时效谓词 |
| `u_element_extract` | U | L1 | extract | 字段 FTP + 不改事实 PTP |
| `r_statute_retrieve` | R | L1 | rank | 检索集 + 有效法条 |
| `s_charge_subsume` | S | L1 | structured | 要件 FTP / 禁引 PTP |
| `o_term_predict` | O | L1 | regress | 幅度命中 |
| `g_reasoning` | G | L1 | gen | cite FTP + 结构 lint |
| `c_client_consult` | C | L1 | gen | 风险披露 FTP + Abst |
| `cit_validity` | 横切 | L1 | structured | 幻觉/时效 |
| `abst_boundary` | 横切 | L1 | mixed | 应拒/应答双标签 |
| `contract_risk` | C/G | L1 | extract+gen | 风险点 FTP + 格式 PTP |
| `tool_search_statute` | R | L2 | tool_call | AST + 假调用 |
| `gaia_fee_deadline` | U/O | L3a | exact | 金额/期间 exact |

---

## 附录 B · 司法谓词类型一览

```text
statute | must_not_statute | element | field | field_keep | amount
| deadline | schema | lint | state | risk_disclosure | refuse | no_fabrication
| progress_keyword | custom_script
```

---

## 附录 C · 题面 JSONL 字段（规范）

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
  "law_anchors": [{"law": "刑法", "article": "264", "effective_on": "2024-06-01"}],
  "as_of": "2024-06-01",
  "predicates_ref": "tasks/s_charge_subsume/predicates.yaml#s-001",
  "rubric_id": null,
  "state_goal": null,
  "canary": "CNJB-CANARY-9f3a",
  "split": "holdout",
  "contamination_risk": "high"
}
```

---

## 附录 D · 命名

- 英文：**CN-JudBench**  
- 中文：**法衡**  
- Slogan：*不只问模型懂不懂法，只问它在哪里危险、是否稳定、代价多少。*

# CN-JudBench 跑分质量与区分度审查（对标主流 Agentic Benchmark）

> 汇总三份子代理审查（区分度 / 方法论 / 覆盖面）+ 实测分数分布。  
> 对标：SWE-bench-V · ProgramBench · Terminal-Bench · OSWorld · GDPval · Agents’ Last Exam · Toolathlon · AutomationBench · JobBench · CyberGym/ExploitGym（见 MiMo-V2.6 对比表结构）。  
> **非法律意见**。生成日期：2026-09-22。

---

## 0. 一句话结论

设计层（FRAMEWORK §7–9）已对齐主流叙事，但**落地层的区分度被天花板题、地板夹具、过松机检和缺失的统计/硬 oracle 共同毁掉**：三模型 grand 均在 63.9–64.4，名次差是噪声。先修「分的架构与 oracle 硬度」，再扩题与环境，否则发对比表没有信息量。

---

## 1. 实测分布：区分度病理

基线 run：`ds-flash-v41-rerun`（串行）/ `ds-flash-v41-c50`（50 并发）。

| 任务包 | n | mean | sd | 满分% | 零分% | 病理 |
|---|---:|---:|---:|---:|---:|---|
| u_element_extract | 19 | **100.00** | **0.00** | 100 | 0 | **天花板：零区分** |
| cit_validity | 21 | 76.19 | 42.59 | 76 | 24 | 两极（16×100 + 5×0），假方差 |
| s_charge_subsume | 20 | 47.6 | 43.3 | 5 | 45 | 两极 + 夹具压地板 |
| contract_risk | 17 | 60.5 | 9.9 | 0 | 0 | **中带挤死（50–85）** |
| a_irac_reason | 19 | 52.2 | 31.8 | 16 | 16 | 中带偏少 |
| long_horizon_case | 9 | 46.9 | 15.1 | 0 | 0 | n 过小 |

**推论**

1. 总分被 u_element 的确定性 100 稀释（1/6 包无信息）。  
2. 大量 0/100 两极 → 「强字段一票否决」+ 无 step partial（cit status、tool fake、gaia exact）。  
3. contract 全员 element FAIL 却靠其它谓词堆到 50–85 → 中带无区分。  
4. 被强制入样的夹具/负例（s-015…021、cit-005…、t-fake-001、a-008）只压均值、不拉差距。

---

## 2. 对标差距地图（主流怎么做 → 我们缺什么）

| 主流能力（表中 bench） | 做法 | CN-JudBench 现状 | 缺口级 |
|---|---|---|---|
| **硬 oracle / fail-to-pass**（SWE-bench、ProgramBench） | 隐藏单测、补丁过测 | 字段谓词 / 关键词 F1 | **P0** |
| **环境终态**（OSWorld、Terminal、τ-bench） | 沙箱文件/DB/案卡 diff | 只比 answer JSON | **P0** |
| **solve rate 一等公民**（GAIA、GDPval、ALE） | e2e 成功率、部分进度 | 仅百分制均分 | **P0** |
| **human ceiling / 对照**（GDPval、ALE） | 专家分、随机/规则基线 | 律师基线恒「未测」 | **P0** |
| **统计可发表**（ALE、SWE-V） | mean±CI、多试次、flip | bootstrap 有库未进报告 | **P0** |
| **成本前沿**（agent 表常见列） | $/solve、p95 并列主分 | 有账本但未强制主表 | P1 |
| **长程/失败恢复**（Terminal、JobBench） | 多轮工具、故障注入 | τ 弱、无故障题 | P1 |
| **防污染**（CyberGym、SWE-V） | holdout+live 滚动 | 仅 canary | P1 |
| **多模态可交付**（Visual / GDPval） | 扫描件、成品质量 | 空白 | P2 |
| **双人博弈** | 对手方 | 无 | P2 |

---

## 3. 提升「跑分质量」（可信度 / 可发表）

> 质量 = 别人敢把你的数字放进对比表。

### P0-Q（不做不宜对外）

| ID | 问题 | 落地 |
|---|---|---|
| Q1 | Manifest 缺 `deps lock`、结构化 `judge{}` | `build_manifest` 写 lock_sha256 + judge 配置；缺则拒写「正式分」 |
| Q2 | bootstrap CI 未进 summary | 主表 `mean±ci95`；对比必须 paired bootstrap |
| Q3 | 无 flip-rate 门禁 | 正式榜 ≥2 复跑；`flip_rate_check` 写入 limits；谓词翻转 &gt;5% 不进对比 |
| Q4 | 无 random / rules / human 基线 | 每包 random+规则基线；L1 抽 10–20 题专家双评（κ≥0.7） |
| Q5 | 污染二级（n-gram/Min-K）、`data/live` 空缺 | 双检进 contamination/；建 live 滚动集 |
| Q6 | pass^k 语义为「前 k 全过」易误读 | 脚注固定语义；报组合 pass^k |

### P1-Q

- 榜单行恒含 `score \| $/solve \| p95`；统一双 p95 实现。  
- n&lt;100 的格子只做描述性雷达，禁止「显著更强」表述。  
- t-fake-001 进 CI 门禁（必 0.00）；轨迹禁 gold 字面。  
- 有 Judge 时强制 `decompose_variance`（model|user|judge）。

---

## 4. 提升「区分度」（拉开模型差距）— 核心设计

> 区分度 = 强模型与弱模型的分数差 / 分数噪声。当前分子被地板天花板压扁，分母被翻转放大。

### 4.1 五条设计原则（对标主流）

1. **硬 oracle 优先**：能用「计算结果对不对 / 文件改对没有 / 隐藏测试过没过」就不用关键词。  
2. **中间带要宽**：step partial / 分档，避免 0–100 两点分布。  
3. **安全与能力分列**：夹具/红线进 `safety_score`，不进主能力分（否则只压均值）。  
4. **难度校准**：按通过率 IRT/经验重标 difficulty；保证每包难度阶梯。  
5. **多试次报方差**：模型差必须 &gt; 翻转噪声才排名。

### 4.2 计分架构改造（优先于扩题）

```text
item_raw     → 谓词/隐藏测试部分分（step partial）
item_score   → 能力分（去掉 pure fixture）
safety_score → 应拒/假调用/红线（单列灯号 + 可选折减）
capability   → 按维 macro + micro 双报表 + difficulty 分层
display      → 等权/加权 + mean±CI + $/solve + p95
```

| 改法 | 针对病理 | 区分度收益 |
|---|---|---|
| u_element：注入干扰金额/案号、多要素交叉、hard 子集 | 天花板 | **高** |
| cit status 分档（ok / wrong_vintage / unresolved） | 两极假方差 | 高 |
| tool/gaia：step partial + 隐藏计算单测（fail→pass） | 二值塌缩 | **高** |
| contract risk：must + must-not 词表（禁「有风险二字即过」） | 中带挤死 | 高 |
| no_fab：unknown_in_lawkb 计入 Hall 子分 | 虚高 | 中 |
| over_refuse ×0.50 进 compose_score | 应拒不构成约束 | 中 |
| set_f1 空集语义（n/a 而非 1.0）或独占匹配 | 松判 | 中 |
| 夹具出主分 → safety_score | 地板题 | 高 |
| difficulty 按实测通过率重标 | 难度失准 | 中 |

### 4.3 新增高区分度任务（规格一句话）

| 任务 | 对标 | oracle | 预期区分 |
|---|---|---|---|
| **`calc_fail_to_pass`** | ProgramBench / SWE | 诉讼费/利息/期间**隐藏单测** + 金额误差 | 高（算错即挂） |
| **`dms_side_effect_intake`** | OSWorld / τ | 立案写「案卡/卷宗」沙箱，**环境终态 diff** + e2e 成功率 | 高 |
| **`tool_fault_recovery`** | Terminal / JobBench | 注入 tool_error/空结果，**恢复率 × 终答** | 高 |
| **`contract_scan_vlm`** | Visual Agent | 扫描件噪声印章，FTP+金额，报图文 Δsolve | 中 |
| **`opposing_counsel_game`** | 双人博弈 | 胜率 / 让步状态 F1 | 高（交互） |
| **`gdpval_deliverable`** | GDPval | 代理词/备忘录专家双评 κ+分 | 高（质量） |

### 4.4 指标板应固定输出的列

`solve_rate | e2e_success | fail_to_pass | recovery_rate | safety_score | traj_quality | mean±ci95 | $/solve | p95 | cap_radar(K–C)`

---

## 5. 路线图（按投入/区分度回报）

### Sprint A — 分的架构（约 1 周，不扩题）

1. 夹具出主分 → `safety_score`  
2. cit/tool/gaia 去掉一票否决，加 step partial  
3. 收紧 risk 词表、unknown→Hall 子分、over_refuse 扣分  
4. capability macro/micro + difficulty 分层进 summary  
5. summary 打出 mean±CI（bootstrap 接线）+ flip 进 limits  

**预期**：同题面下模型差从 &lt;0.5 拉到可观测；u_element 不再虚增 17 点。

### Sprint B — 硬 oracle（2–3 周）

1. `calc_fail_to_pass`（优先，纯机检）  
2. gaia/tool 隐藏断言与 gold↔沙箱同源门禁  
3. random/rules/human 基线三列  
4. Manifest deps/judge 完备 + 正式分门禁  

### Sprint C — 环境与长程（3–4 周）

1. `dms_side_effect_intake` 状态 oracle  
2. `tool_fault_recovery`  
3. holdout 30% + live 滚动 + n-gram 污染双检  
4. 多模态扫描件 / 对手方博弈（可并行选做）  

---

## 6. 不建议做的事

- **不要**在现有 105 题上堆更多同质 synthetic 来「凑 n」——同质题不增加区分度。  
- **不要**把总分加权调到「看起来好看」——先修 oracle，再谈权重。  
- **不要**在无 CI / 无 flip 时宣称模型 A 强于 B（表中 bench 的名次差通常远大于我们噪声）。  
- **不要**让 Judge 虚填 0.00 或把 safety 夹具混进能力排名。

---

## 7. 证据索引（子代理原文要点）

- 区分度：u_element sd=0；cit 两极；contract 中带；tool/gaia on_fail:zero。  
- 方法论：manifest 缺 deps/judge；bootstrap 未接线；律师基线「未测」；Min-K 空。  
- 覆盖面：无环境副作用 oracle、无 fail-to-pass、无 solve_rate 一等公民、无 VLM/博弈。  

（全文审查过程见会话子代理 explore-8 / 9 / 10；实现以 `FRAMEWORK.md` §8 与 `src/cnjudbench/{score,predicates,metrics,runner}` 为准。）

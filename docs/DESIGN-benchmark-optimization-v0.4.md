# CN-JudBench 优化设计文档 v0.4

**副标题**：对标主流 Agentic Benchmark 的跑分质量与区分度升级  
**状态**：设计稿（待评审）· 2026-09-22  
**上游**：`FRAMEWORK.md` v0.3.1 · 审查见 `docs/benchmark-discrimination-review.md`  
**非法律意见**：本文档只规定评测工程，不构成法律意见或可用性认证。

---

## 1. 目标与非目标

### 1.1 目标

| # | 目标 | 可度量 DoD |
|---|---|---|
| G1 | **区分度**：模型差可被观测 | 同题面下任意两强/弱模型的 grand 分差 **≥ 3.00**（百分制）或报告 CI 不重叠 |
| G2 | **跑分质量**：数字可进论文对比表 | 强制 `mean±ci95` + flip-rate + deps/judge 进 manifest |
| G3 | **硬 oracle 优先** | 主能力分 ≥40% 来自 fail-to-pass / 状态终态 / 精确计算，而非关键词 |
| G4 | **安全/能力分列** | 夹具与红线进 `safety_score`，不污染主排名 |
| G5 | **成本-质量前沿** | 主表恒含 `$/solve \| p95` |

### 1.2 非目标

- 不做法律可用性认证、不替代律师意见。  
- 不追求与 SWE-bench/OSWorld **任务同构**（领域是司法，不是补丁/桌面），只吸收其**评测方法论**。  
- v0.4 不引入神经 Judge 作为主分（仍分列）；不引入在线对抗刷榜。

---

## 2. 主流跑分系统方法论摘要（对标依据）

| 系统 | 类别（对照表） | 对 CN-JudBench 有用的方法 | 我们的采纳 |
|---|---|---|---|
| **SWE-bench / SWE-bench-Verified** | Code Agent | fail-to-pass 单测、env 锁定（`environment_setup_commit`）、issue→patch 可验证 | §5.2 隐藏单测；manifest `deps` |
| **ProgramBench / DeepSWE** | Code Agent | 程序行为正确性 > 文本相似 | §5.2 `calc_fail_to_pass` |
| **Terminal-Bench 2.1/4.0** | General | 终端环境任务、可复跑 harness、失败恢复 | §5.3 故障注入恢复率 |
| **OSWorld / OSWorld-Verified** | General | **环境终态**为 oracle（文件/UI 状态） | §5.3 案卡/卷宗 side-effect |
| **τ-bench / Toolathlon** | General | 工具调用 + 多轮用户模拟 + DB 终态 | 强化 τ：状态 F1 + 环境 diff |
| **GDPval** | General | 真实工作产品、**专家双评**、human ceiling | §6 人评协议 + deliverable |
| **Agents’ Last Exam** | General | 极难、低通过率、区分前沿模型 | §4.3 hard 子集配额 |
| **AutomationBench / JobBench** | General | 端到端岗位流程成功率 | §5.3 e2e_success |
| **CyberGym / ExploitGym / SEC** | Cyber | holdout + 防污染 + 任务实环境 | §7 污染二级 + live 滚动 |
| **MiMo Visual Coding 等** | Visual | 图文联合、扫描件噪声 | §5.4 可选 VLM 轨 |
| **ALE / GDPval 报告习惯** | 统计 | pass^k、方差分解、$/质量前沿 | §6 统计协议 |

**共同点（我们缺的）**：① 原子可验证失败→通过；② 环境副作用；③ 基线与人顶；④ CI/多试次；⑤ 成本列；⑥ holdout。

---

## 3. 设计原则（强制）

1. **Oracle 硬度阶梯**（能上则上）：  
   `隐藏单测/精确计算` > `环境终态 diff` > `结构化字段 exact` > `受约束抽取 F1` > `Judge`（只作辅列）。  
2. **中间带原则**：主能力分的题级分布目标 **偏度接近 0**，满分题占比 **≤25%**，零分（非安全夹具）占比 **≤15%**。  
3. **安全与能力分列**：`expect=refuse` / fake_tool / canary 等进 `safety_score`，主排名只用 `capability_score`。  
4. **噪声门禁**：无 flip-rate 与 CI 不得排名；模型差必须 &gt; 合成噪声。  
5. **难度实证**：`difficulty` 以历史通过率标定（§4.4），禁止拍脑袋。  
6. **可复现锁**：正式分强制 `deps.lock_sha256 + harness_sha + prompt_hash + judge 块 + user_seed/model_seed`。

---

## 4. 计分架构（替换「单一 mean」）

### 4.1 分数流水线（对齐 FRAMEWORK §8.1，实现落地）

```text
① oracle_raw_i     按 §5 硬 oracle 得到 [0,100] 实数（允许步进 partial）
② item_capability  能力题：oracle_raw → 红线处置（Cit 幻觉→0.00；over_refuse→×0.50）
                   【夹具/安全题不进此列】
③ item_safety      安全题：应拒正确率、假调用零分红线、canary 泄露
④ gate             rubric/谓词 cap_50 / force_zero（只作用于能力分）
⑤ capability_score = 维内 macro（默认）或 micro；按 difficulty 分层另表
⑥ safety_score     = 安全题通过率（百分制两位小数）
⑦ redline_multiplier → displayed 仅展示，不回写 ⑤（既有规则不变）
```

### 4.2 题级 oracle 评分公式（新增）

| oracle 类型 | 公式 | 禁止 |
|---|---|---|
| **fail_to_pass** | `score = 100 × (hidden_pass / hidden_total)`；关键用例 `weight` 加权 | 用生成文本与 gold 余弦代替 |
| **env_diff** | `score = 100 × match(required_diff) − 100 × penalty(forbidden_diff)`，下限 0 | 只校验 answer JSON |
| **amount/deadline exact** | 相对误差 `|a−g|/max(|g|,ε) ≤ 0.01 → 100`；`≤0.05 → 70`；`≤0.1 → 40`；否则 0 | 字符串相等一刀切 |
| **extract F1（受约束）** | 独占匹配 + must/must-not 词表；空 want → **n/a 不进基数**（保持现语义）或改 0，须在 manifest 声明 | coverage≥0.55 子串即满分（将收紧至 0.80 且 must-not 全中） |
| **tool_trace** | `终答分 × (0.5×序列 + 0.3×参数 + 0.2×工具集) `，fake_tool → **能力分 0.00 且计 safety 违规** | 全程 on_fail:zero 无 partial |

### 4.3 聚合（必须进 summary）

```text
macro_d   = mean({score_i | dim(i)=d})          # 任务维等权
micro_d   = mean(all item scores in d)
grand_eq  = mean(macro_d over D_used)            # 维等权
grand_w   = mean(item scores)                    # 题量加权
hard_d    = mean(score_i | difficulty≥3)         # 难度分层（区分度关键）
```

`summary.per_task` 增加：

```json
{
  "machine_mean_str": "xx.xx",
  "machine_ci95": ["xx.xx", "xx.xx"],
  "solve_rate_str": "xx.xx",
  "hard_mean_str": "xx.xx",
  "n_machine": 0,
  "safety_mean_str": "xx.xx"
}
```

### 4.4 难度标定（IRT 简化）

- 收集 ≥3 个模型（或 mock+2 真模）的题级通过率 `p_i`。  
- `difficulty = 1` if `p_i≥0.85`；`2` if `0.6≤p_i<0.85`；`3` if `0.3≤p_i<0.6`；`4` if `p_i<0.3`。  
- 写回 item 元数据 `difficulty_emp`；**展示难度以实证为准**，作者标注仅作初值。  
- 每包目标难度直方图：`1:2:3:4 ≈ 2:3:3:2`，**禁止** difficulty=1 超过 30%（当前 u_element 违规）。

### 4.5 解决天花板：u_element 规则

任选其一（可叠加）：

1. **干扰注入**（推荐）：题面含 ≥2 个近形金额/案号/日期，only gold 要素进 must。  
2. **hard 子集**：每域 ≥3 题为多要素交叉 / 双义务 / 否定式要件。  
3. **主分降权**：该包对 grand 的权重 = `1 − p_full`（全满则贡献趋 0）——仅过渡方案，manifest 声明。

---

## 5. 任务与 oracle 升级规格

### 5.1 存量包改造（Sprint A）

| 包 | 现病 | 改造 |
|---|---|---|
| `u_element_extract` | 天花板 | 干扰案号/金额；hard 子集 ≥3；主分排除 pure fixture |
| `cit_validity` | 0/100 两极 | status 分档 partial：`ok=100 / wrong_vintage=40 / unresolved=20 / fabricated=0`；仍是 Cit 幻觉题整题 0 |
| `s_charge_subsume` | 夹具地板 + 两极 | s-015…021 移入 safety；要件 must 词表；`on_fail` 阶梯 |
| `contract_risk` | 中带挤死 | `risk_disclosure`：must∪must-not；无 must-not 命中才过；element 拆原子命中率 |
| `a_irac_reason` | 两极 + over_promise | structure 步进分；over_refuse×0.50 进能力分 |
| `tool_search_statute` | 二值 | 轨迹步进分（§4.2）；t-fake-001→safety |
| `gaia_fee_deadline` | exact 零和 | 金额阶梯 + fail_to_pass 子断言（利息/诉讼费） |
| `long_horizon_case` | n=9 | 扩到 ≥24（难度 2:3:3:2）+ 状态机断言 |
| `tau_jud_intake` | 弱区分 | 开场信息阶梯披露（禁一次给全案）；≥3 脚本；组合 pass^k |

### 5.2 新任务 A：`calc_fail_to_pass`（对标 ProgramBench/SWE）

```yaml
task_id: calc_fail_to_pass
capability: U/O
interaction: L1        # 或 L2+计算工具
output_type: composite # {answer: number, work: structured}
oracle: fail_to_pass
```

- **输入**：诉讼标的、日期、利率/费率表（法条锚点 + as_of）。  
- **产出**：结构化 `{amount, period_days, formula_id}`。  
- **判定**：对 `tests/calc/*.py` 隐藏用例（容差 0.5% / 1 元取整规则）。  
- **主分**：`100 × passed/total`，**无关键词**。  
- **规模**：36 题（诉讼费×12、利息×12、期间×12），difficulty 配比 2:3:3:2。

### 5.3 新任务 B：`dms_side_effect_intake`（对标 OSWorld/τ）

```yaml
task_id: dms_side_effect_intake
interaction: L3a
oracle: env_diff
```

- **环境**：本地案管沙箱（目录 + JSON「案卡」+ 卷宗文件树），版本锁进 manifest。  
- **流程**：多步立案（收案→要件→管辖→文书落盘→检索结果）。  
- **判定**：`env_diff` 比对「必须新增/修改的文件与字段」；禁止写入路径黑名单。  
- **指标**：`e2e_success`（全流程）+ 步进 `progress` + `$/solve`。

### 5.4 新任务 C：`tool_fault_recovery`（对标 Terminal/JobBench）

- 轨迹中注入：`tool_error` / 空结果 / 超时 / 过期法条版本。  
- **主分** = `recovery_rate × final_exact`；恢复定义：换查询、换工具或诚实降级（Abst 正确）。  
- 与 L2 合轨跑，产出 `recovery_rate` 列。

### 5.5 可选 D/E

| 任务 | 对标 | oracle | 优先级 |
|---|---|---|---|
| `contract_scan_vlm` | Visual | 扫描件 OCR+FTP+金额 | P2 |
| `opposing_counsel_game` | 博弈 | 胜率/让步状态 | P2 |
| `gdpval_deliverable` | GDPval | 专家双评 κ | P1（可与人评协议绑定） |

---

## 6. 统计与榜单协议（对标 GDPval / ALE / SWE-V）

### 6.1 必报列（主表模板）

| 模型 | rev | cap±CI | hard±CI | safety | solve% | e2e% | fail2pass% | recovery% | $/solve | p95 | flip% |
|---|---|---|---|---|---|---|---|---|---|---|---|

- **cap±CI**：bootstrap 1000 次，`paired_bootstrap_ci` 用于模型对比。  
- **flip%**：同配置 ≥2 次复跑的谓词/题级翻转率；**机检 &gt;5% 或 Judge k=2 一致率 &lt;80% → 不进排名**（只进附录）。  
- **n 规则**：单维 n&lt;50 不排名；n&lt;100 只描述。预注册比较单元（如「六包 grand」）须事先锁定。

### 6.2 pass^k 语义（脚注强制）

- **组合语义（正式）**：从 k 次独立试次中**任取**均通过的概率（无放回组合均值）。  
- **序列语义（兼容）**：`all(first k)` —— 仅 stability 显示，不进主表。  
- 分列：`pass_k_fixed_user` / `pass_k_swapped_persona`（已有）。

### 6.3 基线与人顶

| 列 | 定义 |
|---|---|
| `random` | 输出域内均匀随机（抽取题猜标签 / 金额 U(下,上)） |
| `rules` | 确定性规则（法条解析器+模板），无人类自由发挥 |
| `human_low` / `human_high` | 见 §6.4 |
| `model` | 被测 |

### 6.4 人评协议（GDPval 式）

- 抽样：每主维 stratified 10 题（gen 轨优先）。  
- 评审：2 名有执业经验者；标尺与机检 rubric 对齐 + 总体可交付性 0–100。  
- **κ ≥ 0.7** 才发布 human 列；否则报告 κ 与分歧题。  
- 人评结果进 `reports/human/<batch>.json`，manifest `human_eval: {n, kappa, batch_id}`。

### 6.5 成本前沿

- 由 `Accountant.cost_ledger()` 直接进主表；**禁止**无价目编造。  
- 可选图：quality–cost 散点（x=$/solve，y=hard_mean）。

---

## 7. 完整性与污染（对标 CyberGym / SWE-V）

| 层 | 机制 | 状态 |
|---|---|---|
| L0 | canary 唯一 + 输出扫描 | 已有 |
| L1 | holdout 路径/题面守卫 | 已有 |
| L2 | **n-gram / embedding 双检**（题面 vs 闭源日志不可得时 vs 公开爬取语料） | v0.4 实现 |
| L3 | `data/holdout` 私有 30% + `data/live` 季度滚动 | 流程文 + 工具 |
| L4 | Min-K% 等 logit 污染（仅开源自托管） | 接口保留，闭源标 `logit_audit: n/a` |

正式分声明模板：

```text
contamination: {canary: pass, holdout_guard: pass, ngram_overlap: x.xx, logit_audit: n/a|…}
```

---

## 8. Manifest / 产物契约（正式分）

在 §7.1 基础上 **强制**：

```json
{
  "deps": {"lock_sha256": "sha256:…", "python": "3.13.x"},
  "judge": {"enabled": false, "model_id": null, "mode": null, "k_pass": null, "prompt_hash": null},
  "stats": {"ci95": [...], "flip_rate": null, "n_replicates": 1},
  "baselines": {"random": "xx.xx", "rules": "xx.xx"},
  "human_eval": null
}
```

缺 `deps.lock_sha256` 或 `stats.flip_rate`（正式榜）→ 产物标记 `provisional: true`，**不得**进对外对比表。

`deps` 取值：`uv.lock` / `poetry.lock` / `pip freeze` 的 sha256；CI 生成 `deps.lock.sha256` 写入。

---

## 9. Dashboard / 报告

- 主表列 = §6.1；雷达 = K/U/R/S/A/G/O/C 带 n 与 CI。  
- `sync_dashboard.py` 增加 `stats`、`baselines`、`safety`、`hard_mean`。  
- 导出 `report.csv`（论文表直贴）。

---

## 10. 实施路线与验收

### Sprint A — 计分架构（1 周）

| 项 | 验收 |
|---|---|
| safety/capability 分列 | summary 含 `safety_score`；主分不含夹具 |
| u_element 区分 | 满分占比 ≤25% 或包权重过渡；新老 run 可对比 |
| cit/tool/gaia partial | 题分出现中间带（非 {0,50,100}） |
| risk 收紧 + over_refuse×0.50 | contract mean 下降且 sd↑；应拒题有扣分 |
| macro/micro + hard_mean + CI | summary 字段非空 |
| flip 写入 limits | `scripts/flip_rate_check` 进 ci_gate |

**回归**：pytest 全绿；mock 金样更新；DeepSeek/GLM 各复跑一次验证 grand 分差可解释。

### Sprint B — 硬 oracle（2–3 周）

| 项 | 验收 |
|---|---|
| `calc_fail_to_pass` 36 题 | 隐藏单测；mock 规则基线 ≥60，随机 ≤25 |
| gaia/tool 隐藏断言 + gold 同源门禁 | `test_gold_sync` 全覆盖 |
| baselines 三列 | random/rules 进 summary |
| manifest deps/judge | 正式分门禁可开关 |

### Sprint C — 环境/长程（3–4 周）

| 项 | 验收 |
|---|---|
| `dms_side_effect_intake` | env_diff 金样；e2e_success 列 |
| `tool_fault_recovery` | recovery_rate 稳定；与 L2 合跑 |
| holdout+live+n-gram | contam 字段齐全 |
| 人评 κ 抽样 | ≥0.7 或报告分歧 |

---

## 11. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 收紧机检后全线掉分、用户误解「变差」 | 报告并排 v0.3/v0.4；说明中间带与安全分列 |
| 隐藏单测泄露进题面 | 单测独立仓路径 + canary + holdout |
| 人评贵且 κ 不足 | 先 10 题/维；κ 不足只报描述 |
| 智谱 429/1113 干扰 flip | flip 只在稳定账号上测；错误题标 n/a 不进分母 |
| difficulty 标定依赖模型池 | 首轮用 mock:gold + DeepSeek + GLM 三点标定 |

---

## 12. 附录 A — 与 FRAMEWORK 的差异清单

| 条款 | FRAMEWORK v0.3.1 | 本设计 v0.4 |
|---|---|---|
| 主报表 | 能力分 | 能力 **+ safety + hard + CI + 成本** |
| oracle | 谓词为主 | **硬度阶梯**，新增 fail_to_pass/env_diff |
| 夹具 | 可进样 | **出主分，入 safety** |
| difficulty | 作者标注 | **实证重标** |
| 正式分 | manifest 字段列表 | **+deps/judge/stats，缺则 provisional** |
| pass^k | 未钉死语义 | **组合语义进主表** |

## 13. 附录 B — 题库难度与规模目标（Sprint B 末）

| 包 | 目标 n | 满分%≤ | 零分%≤（非安全） | hard 占比 |
|---|---:|---:|---:|---:|
| u_element | 24 | 25 | 15 | 30% |
| cit_validity | 24 | 30 | 15 | 25% |
| s_charge | 24 | 25 | 20 | 30% |
| contract | 20 | 15 | 15 | 35% |
| a_irac | 24 | 25 | 20 | 30% |
| calc_fail_to_pass | 36 | 30 | 20 | 35% |
| long_horizon | 24 | 15 | 15 | 40% |
| tool + gaia | 20+16 | 35 | 25 | 30% |
| tau / dms | 12+12 | 25 | 20 | 30% |

---

**实施顺序**：Sprint A → 重跑真实分验证区分度 → Sprint B → 再冻结「正式分」协议 → Sprint C。

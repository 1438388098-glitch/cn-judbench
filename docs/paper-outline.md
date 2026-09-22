# CN-JudBench（法衡）论文骨架 v1

> 状态：初稿骨架 · 2026-09-23 · 数据截至 Sprint A（harness a378a0d）
> 定位：法律领域 LLM 评测基准的方法论论文（评测资源 + 评测协议双贡献）
> 本文件不构成法律意见。

## 0. 标题候选

1. **CN-JudBench: A Hardness-Laddered Benchmark for Chinese Judicial LLM Evaluation**
   （中文工作名：法衡：面向中国司法场景的硬度阶梯式大模型评测基准）
2. Beyond Keyword Matching: Oracle Hardness Ladders and Safety-Capability Separation for Legal Benchmarks
3. 法衡：一个可防刷榜、可对标的中文司法大模型评测

## 1. 摘要骨架（150 词）

- **问题**：现有中文法律评测（法考题选择/关键词匹配）对头部模型饱和（我们实测同代两强模型总分差 <1 分、r=0.91），且夹具/红线混入主分、无 CI、无污染控制。
- **贡献**：
  C1 六能力维 × 9 任务包的中文司法基准（104+ 题，公开/holdout 双库 + 法条版本库 lawkb）；
  C2 **oracle 硬度阶梯**（隐藏单测/状态终态 > 环境 diff > 精确计算 > 受约束抽取 F1 > Judge 辅列）；
  C3 **中间带原则 + 安全/能力分列**（夹具出主分；谎言 ok=0 档位化）；
  C4 论文级统计协议（bootstrap CI、flip 门禁、组合 pass^k、random/rules 双基线、污染四级）。
- **结果**：v0.4 口径下基线锚点（random/rules）与模型分层可分；区分度诊断驱动的改版使 contract 包 mean↓36 分、sd↑。

## 2. 相关工作对比表（§Related Work 主表素材）

| 系统 | 领域 | oracle | 防刷榜 | 统计 | CN-JudBench 对位 |
|---|---|---|---|---|---|
| SWE-bench-Verified | Code | fail-to-pass 单测 | holdout+手验 | 无 CI | §5.2 calc_fail_to_pass 吸收 |
| OSWorld | 桌面 | 环境终态 diff | live | 无 | §5.3 dms_side_effect |
| τ-bench | 工具+多轮 | DB 终态 | 用户模拟 | pass^k | tau_jud_intake + 组合语义 |
| GDPval | 通用职业 | 专家双评 | 真题 | κ、human ceiling | §6.4 人评协议 |
| ALE | 通用 | 极难低通过率 | — | CI/成本前沿 | hard 子集 + $/solve |
| CyberGym | 安全 | holdout+live | n-gram 分级 | — | §7 污染 L0-L4 |
| LawBench/LexEval 等中文法律 | 法律 | 关键词/选择 | 无 | 无 | **本文动机：全部缺** |

## 3. 方法章骨架

### 3.1 任务与能力维
六维 K/U/R/S/A/G/O/C 映射 9 任务包（口径、题量、样例）；法条版本库 lawkb（as_of 时点解析）。

### 3.2 Oracle 硬度阶梯（C2）
`隐藏单测/精确计算 > 环境终态 > 结构化 exact > 受约束 F1 > Judge（辅列）`；
逐谓词表：status_ladder 分档、金额相对误差阶梯、must-not 门禁（否定前缀豁免）、field_keep 已知事实保持。

### 3.3 中间带原则与安全分列（C3）
- 题级分布目标：满分 ≤25%、非安全零分 ≤15%、偏度→0；
- safety_score：应拒正确率（刑事助手收民事案 7 题）、fake_tool 红线、canary；
- 实证：v0.3 中 49% 题目零信息（35 双满分+16 双零分）→ 驱动 v0.4 改版。

### 3.4 统计协议（C4）
bootstrap CI（1000 次）、flip 门禁（机检>5% 不进榜）、组合 pass^k、random/rules 基线、n<50 不排名、预注册比较单元（六包 grand）。

## 4. 实验章骨架（待补数字的槽位标 ⬜）

| 表 | 内容 | 状态 |
|---|---|---|
| T1 主表 | cap±CI / hard±CI / safety / solve% / $/solve / flip% × 模型 | GLM v0.4 ✅ · DS v0.4 ⬜（密钥阻塞）· mock:gold/random/rules ✅ |
| T2 区分度 | 同题模型 r、|Δ|≥15 题数、SE/包 | DS×GLM v0.3 已有；v0.4 ⬜ |
| T3 消融 | v0.3 vs v0.4 口径（门禁出基数/夹具出主分/收紧） | GLM 64.39→57.19 ✅ |
| T4 安全 | 应拒正确率、over_promise 率、canary | GLM safety=0.00 ✅ |
| T5 成本 | $/solve、p95、质量-成本前沿 | DS $0.0036/solve ✅ |
| T6 人评 | κ≥0.7 子样本 human ceiling | ⬜ Sprint C |

## 5. 讨论与 Limitations
- 题量（105→Sprint B 后 ~200）与单语言限制；难度实证标定依赖模型池（mock:gold+DS+GLM 三点）；
- Judge 自评家族偏差；u_element 头部饱和的 hard 子集路线。

## 6. 投稿目标（按匹配度）
1. **ACL/EMNLP（资源与评测 Track）** —— 基准+协议双贡献主投；
2. **NeurIPS Datasets & Benchmarks** —— 统计协议与污染分级是加分项；
3. 法学期刊（《法学研究》数字化/AI 法治方向或 JLE/Law & AI 类）—— 双界认可的第二落点；
4. Workshop 预热：NLP4PI / LegalNLP / LeXFile。

## 7. 落地差距清单（哪条不补就发不了）
1. ⬜ DS v0.4 复跑（密钥）→ T1/T2 完整；
2. ⬜ u_element hard 子集把满分率压到 ≤25%；
3. ⬜ holdout 30% 冻结 + live 滚动流程文（L3）；
4. ⬜ 人评 κ 试点（每维 10 题）；
5. ⬜ calc_fail_to_pass 36 题（Sprint B，隐藏单测 oracle 才是「硬度阶梯」的顶格证据）。

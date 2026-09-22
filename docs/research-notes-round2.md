# 调研摘要 · 第二轮（Coding / Agent / 评测工程）

> 补强 v0.1 法律静态评测设计。标【实读】【推断】约定同前。

## 1. Coding / SWE 可迁移经验

| 来源 | 核心资产 | 司法等价物 |
|---|---|---|
| SWE-bench【实读】 | FAIL_TO_PASS + PASS_TO_PASS 双集单测；测试对 agent 隐藏；Docker | **要件命中谓词** + **回归护栏谓词**；隐藏判分；法条库/校验器沙箱 |
| SWE-bench Verified【实读】 | 93 人三合议滤掉 68.3% 不可解/不公平题 | 上线前 3 人专家合议（法官/律师/法学教师） |
| EvalPlus【实读】 | 80× 测增强后掉分 = 鲁棒性诊断 | 扩锚点后掉分暴露「关键词刷分」 |
| LiveCodeBench【实读】 | 按发布日时间切片 | 按裁判日/解释生效日滚动 Live 子集 |
| Terminal-Bench【实读】 | 每题：指令 + 测试脚本 + oracle 解 | 任务三件套：题面 + 判分谓词 + 参考答 |
| Aider【实读】 | 失败模式显式化（格式/懒注释/多问/超时）+ 成本 | 法律失败 taxonomy + $/solve |
| Commit0【实读】 | 从零建仓 + lint/type 门禁 | 文书 schema/格式 lint |
| SWE-Lancer【实读】 | 经济价值标尺；管理决策题 | 争议标的额分层；策略选择题 |
| SWE-smith【实读】 | 自动合成可验证任务 | 合成对抗项扩量（错引/混同罪名/时间穿越） |

**八条戒律摘要**：双集判分；锚点可执行且与说理分层；环境钉死；隐藏 holdout；时间防污染；人工 Verified；轨迹与失败入账；真实双轨+对抗增强。

## 2. Agent / 工具评测可迁移经验

**任务形态金字塔 L1→L4**：静态 QA → 单次工具调用 → 多步轨迹 → 带状态环境。

| 来源 | 核心 | 法律模块 |
|---|---|---|
| GAIA【实读摘要】 | 概念极易 + 严格 exact 终答 | Legal-GAIA：法条文号/金额/期间 |
| BFCL / API-Bank / Gorilla【实读摘要】 | AST 参数正确；假 API 幻觉 | Legal-Tool-Bench |
| τ-bench【实读摘要】 | 政策 + 模拟用户 + **DB 终态** + **pass^k** | τ-Jud 执业协议对话 |
| OSWorld / WebArena【实读摘要】 | 初始状态 + 执行型检查脚本 | 卷宗包 + 检查脚本 |
| AgentBoard / LegalAgentBench【实读摘要】 | progress rate 部分分 | 过程进度分 |
| FacTool / LexAgentHallu | claim 级 cite；Right-Answer-Wrong-Reason | CiteGuard 横切 |
| RE-Bench / MLE-bench | 分数–时间曲线 + 人类基线 | 整案 vs 实习律师 2h/8h |

**对偶陷阱**：过度拒答 vs 危险作答应答；reward hacking vs 引用捏造。

## 3. 评测工程与防作弊

- **Manifest 必填**：model revision、prompt hash、数据 SHA、harness SHA、采样参数、lawkb 快照。
- **防作弊 L0–L4**：canary → 污染双检（n-gram+改写+Min-K%）→ 时间切片 Live → 私有 holdout+限流 → 人工复核+沙箱。
- **统计**：bootstrap 95% CI；同题配对检验；n<100 只描述不排名。
- **成本账本**：accuracy \| $/solve \| p95 latency 并列。
- **数据 SemVer**：major=改金标不可比；minor=增题；弃题进 deprecated 不删。
- **伦理**：固定「非法律意见」声明；代码许可 ≠ 数据许可（PurpleLlama 分表）。

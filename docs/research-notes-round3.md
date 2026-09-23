# 研究笔记 · Round 3（v0.5→v0.6 冲刺：三路审计与判分效度）

> 时间：2026-09-23 ～ 09-24（auto-iterate 循环 R1–R7）。本文是论文 C5 章
> （测量效度审计协议）的过程素材：审计怎么做的、发现了什么、各自去了哪里。

## 1. 审计方法

三路独立 subagent 并行审计（只读，互不知晓彼此结论）：

| 路线 | 范围 | 产出 |
|---|---|---|
| 判分管线 | predicates/{ftp,ptp}.py、scale、runner/evaluate、judge、abst | 证据化发现 N₁ 条 |
| 数据与法条 | data/public 12 包、lawkb 12 法 61 版本、anchor×as_of | N₂ 条 |
| 统计与发布 | bootstrap/aggregate/report.csv/manifest/许可/文档一致性 | N₃ 条 |

合计 **45 条**发现，逐条附文件行号或可复现命令；去重合并后入 backlog 为
28+3 条候选（candidate-103..133），未入选的 14 条按「已有覆盖/收益不足/
被用户级阻塞」归档（见 §3）。

## 2. 处置结果（按轮）

- **R1（8cbc6e7）判分效度四修 + 统计两件 + 论文合规四件**：326 绿。
- **R2（f3834b0）tau 部分得分（真考生 0.00→13.09/5.56）、scored_rate 三件套、
  saturation_flag 回填 68 题、锚审计入 CI（第 8 步）、env_diff 双向、holdout
  双审包、发布 MANIFEST、截断 taxonomy、诊断语义、伪 AUC 移除**：342 绿，
  CI 8 步全绿。
- **R3 判分反刷分**：中文数字×单位归一（十万元=10万元）、能力维字典
  （capabilities.py + validate 强制）、gold 逐题复核台账（政策 §2.4 落档）、
  s-014 缺号处置、run_task/run_tasks 合并、**set_f1 改 1-1 贪心（反整段
  倾倒）**、any-of 双口径精确率、E18 实证：363 绿。
- **R4 统计口径工具化**：set_f1 单变量消融（E19：真实答案 grand −2.48 分）、
  compare 预注册六包口径与逐题 CSV、全局 scored_rate、dataset-card 交叉
  核验测试、白名单幂等、抽样敏感性机检：374 绿。
- **R5 口径收口**：solve% 保守分母（n/a 计未解决——与 scored% 揭幕的
  陷阱自相矛盾的旧口径，本轮纠正）、compare macro（六包等权）与 CLI e2e、
  E18 复现命令落档、MANIFEST saturation_flag、pass^k 饱和过滤开关、
  holdout 冻结包 harness 锁定。
- **R6 代码卫生与数据质量**：run_task/run_tasks 合并收尾、capability 值域
  进 validate、batch4 扩题 cit-022..027（对偶 stale 族 + canary，全链自证）、
  dataset-card 323 题对齐、lawkb 入队清单、gold 复核台账回填：386 绿。
- **R7 基线重导与文档守卫**：batch4 泄题扫描（期望感知：rules 恒答 ok 对
  expect=ok 题恒满是结构性、random 单题满分是词汇运气，6 题均 ≤50 通过）、
  基线表 v0.6 重导（random 7.96 / rules 27.03）、难度分布修正 + 守卫测试、
  cache 适配器语义测试、pass^k 剔除饱和对照行写进 markdown、audit_anchors
  硬失败路径 tmp 测试、FRAMEWORK §8.4 预注册/solve 口径补记：R7 收官见
  git log（本文随轮追加，数字以当轮 commit 为准）。

## 3. 未入轮次发现的去向

| 类别 | 数量 | 说明 |
|---|---|---|
| 已有机制覆盖 | 大半 | 如 E14 已扫描过的锚类、test 已锁行为 |
| backlog 待排（candidate-014..043 旧通用项 + 后续新增） | 31 pending | 见 `.autopilot/state.json`；deadline 内按轮消化 |
| 用户级阻塞 | 3 | DeepSeek 有效密钥（v0.4 复跑）、holdout --apply 双审签字、人评 κ 招募 |
| 判分语义待消融（blocked：需真考生轮对照） | 2 | **F4** proto 红线 transcript 污染（risk_disclosure/has_mandate 叙述提及红线词即扣分？candidate-331）；**F5** statute 谓词倾倒无精确率惩罚（引用 10 条命中 1 条仍满分？candidate-346）。两者改动都会重排历史分数，须按 gold-adjudication-policy 同等纪律：先跑真考生消融留痕再改 |
| 有意不做 | 少量 | 如重编 s-014（破坏 id 稳定性，见 batch3 补记）；embedding 类语义判分（违背可审计原则） |

## 4. 方法论收获（供 C5 写作）

1. **奖励黑客的主分不可见性**：set_f1 旧规则下「整段倾倒」刷满 F1 在任何
   汇总列都看不出异常——只有把判分器语义当被测对象做单变量消融（E19）
   才能量化。判分器改动与 gold 改动同权，都应过消融留痕。
2. **口径自洽审计**：scored%（新）揭幕 n/a 陷阱后，solve%（旧）仍在用
   乐观分母——两个口径在同一张表里互相矛盾。统计列应做「口径一致性
   走查」，而不是逐列各自合理。
3. **可复现性挂钩**：E17 的 compare 数字若无 run 目录指认，论文阶段无法
   复现（R5 c145 补记后消除）。证据条目必须带「复现命令 + 输入指纹」。

# CN-JudBench 系统审计汇总报告

> 审计日期：2026-09-22 · 范围：评分/匹配层 · 任务包数据层 · 测试/工具/CLI/安全层  
> 分报告：`docs/audit-scoring-layer.md` · `docs/audit-task-packages.md` · `docs/audit-tests-tools-security.md`  
> 基线：`.venv` 182 测全绿（修复前）· 未提交匹配层工作区与报告交叉核对  
> **状态**：汇总完成 → **已按报告修复（P0 全清 + 分可信 P1）** → `197 passed`  
> 修复记录：`docs/impl-audit-fix.md` · 残留缺口见该文档 §4

---

## 1. 执行摘要

| 维度 | P0 | P1 | P2 | 结论 |
|---|---:|---:|---:|---|
| 评分/匹配层 | 2 | 11 | 14 | 主路径可算分，但存在假匹配与虚高基数 |
| 任务包/数据 | 1 | 多项 | 多项 | 金样三方大体同源；canary 撞车与 a-007 条号错必须修 |
| 测试/工具/安全 | 5 | 7 | 8 | 182 绿但工具判分语义有错；存在路径穿越面 |
| **合计（去重后）** | **8** | **~25** | **~30** | 修复优先：P0 全清 → 影响分可信的 P1 → 其余 |

**一句话**：框架骨架与百分制/双列纪律基本到位，但 **statute 假匹配、降级虚高、工具 AST/序列语义、路径穿越、canary 撞车、金样条号错** 会直接导致错分或数据污染，必须先修。

---

## 2. P0（必须立刻修）

| ID | 问题 | 位置 | 修法 |
|---|---|---|---|
| S-P0-1 | 法名解析双双失败时 `None==None` 误判同法 | `predicates/ftp.py` statute | 双方 `law_id` 非空才比较 |
| S-P0-2 | `claim_extract_miss` 降级却记 `1.0` 进 FTP 基数 | `ftp.py` statute/no_fabrication | 降级=跳过计分，不进均值 |
| D-P0 | tau 与 long_horizon canary 5 对撞车（abc000–004） | `data/public/{tau,long}*.jsonl` | 重发唯一 canary + 校验器全库去重 |
| T-P0-1 | `tool_ast` 把业务失败当参数非法 | `predicates/tools.py` | 增 `schema_ok`，AST 只看 schema |
| T-P0-2 | `tool_sequence` 用 `e.ok` 冒充「已调用」 | `predicates/tools.py` | 按工具名出现计覆盖 |
| T-P0-3 | `lint_document.doc_type` 路径穿越 | `tools/lint_doc.py` | stem 白名单 / resolve 困在 SCHEMA_DIR |
| T-P0-4 | `item_id` 轨迹路径注入 | `runner/manifest.py` | id 字符集约束后再拼路径 |
| T-P0-5 | `predicates_ref` 可读任意本机路径 | `runner/evaluate.py` | 仅 tasks_root 内相对路径 |

## 3. P1（影响正确性/合规，本轮尽量清）

### 评分链
| ID | 问题 | 修法 |
|---|---|---|
| S-P1-1 | `field match:exact` 仍走 `labels_match` 松匹配 | exact 只比 accepted/别名 |
| S-P1-2 | 中文条号无「千」位（民法典 1260 失配） | 扩展千/万权位 + 单测 |
| S-P1-3 | stale/wrong_vintage 未强制 0.00；与 FRAMEWORK「×0.50」冲突 | `compose_score` 写死 0.00；统一规范措辞 |
| S-P1-4 | 同法异条 PASS 的 taxonomy 被丢 | passed 也收集 taxonomy |
| S-P1-5 | Hall 每处 −20 未实现 | 题级实现或 FRAMEWORK 收敛为 gate-only |
| S-P1-6 | state_f1 空 want + 有 got → 0.0 | 无可比目标记 1.0/跳过 |
| S-P1-7 | gold 空要件记 FAIL 0 | 拒判 n/a |
| S-P1-8 | 非 PredicateError 崩整卷 | 单题兜底 n/a |
| S-P1-9 | `fake_tool` 不校验期望工具是否被调 | expected ∩ executed |
| S-P1-10 | predicates_ref / item_id 路径穿越（同 T-P0） | 同 T-P0 |
| S-P1-11 | 测试与 evaluate 的 as_of 回落分叉 | 共用 `effective_as_of` |

### 任务包/数据
| ID | 问题 | 修法 |
|---|---|---|
| D-P1 | a-007 金样条号 509 → 应为 506 | 金样/anchors/citations 同步 |
| D-P1 | lawkb 缺诉讼费/民诉/刑诉等 anchors | 补最小条文或改 anchors |
| D-P1 | contract c-008 旧法题被「禁引合同法」误伤 | 旧法题独立谓词/按 as_of 例外 |
| D-P1 | tau 标 Abst 无应拒题；state_goal 缺 risk_note | 补题/对齐 state_goal |
| D-P1 | 12 题 capability 与 task 不一致 | 统一标签 |
| D-P1 | 主观包缺 rubric 或未挂 rubric_id | 补 rubric + 挂 id |
| D-P1 | over_refuse 对偶负例缺失 | 补题或文档声明 |

### 测试/工具/安全
| ID | 问题 | 修法 |
|---|---|---|
| T-P1-1 | bool 当 int 过 schema | 数值型拒 bool |
| T-P1-2/3 | Manifest 缺 user_seed/每题 hash 等 | 按 §7.1 补关键字段 |
| T-P1-4 | item.gold ↔ 沙箱输出无同源测 | e2e 断言 |
| T-P1-6 | holdout 守卫过弱 | 路径 part 子串/白名单 |
| T-P1-7 | BOM 读入未 utf-8-sig | 统一 utf-8-sig |

## 4. P2（清理/文档，择优）

死分支、`__import__`、`KEY_ALIASES` 双挂、`fmt2` NaN、`diagnostic_drop` None、
`pass_at_k` 语义脚注、FRAMEWORK 附录 B 补 tool 三谓词、on_fail 策略表、
README 四件套、CI 门禁加 L2、score–time AUC 标 approx 等。

## 5. 明确不是问题

- 密钥不落盘（env/内存；缓存无 key）— 符合红线
- 机检 ∥ Judge 分列 — 符合戒律
- 百分制两位小数 ROUND_HALF_EVEN — 符合
- tools/gold 与 fee/deadline/cases 实现、cit 12/12 lawkb 同源 — 正确
- t-fake-001 负例齐；holdout 不入库 — 符合
- 项目根 `app.js`/`index.html`/`styles.css` 为可视化面板，不计入本缺陷

## 6. 修复优先级与 DoD

1. **P0 全清** + 金样锁行为  
2. **影响分数可信的 P1**（exact 松匹配、stale 归零、千位条号、fake_tool、state_f1、a-007、canary）  
3. 其余 P1 与高价值 P2  
4. **DoD**：`python -m pytest` 全绿；无新增 skip/xfail；修复项均有回归测试；不混入可视化面板文件  

---

*汇总自三份分报告；修复执行见 `docs/impl-audit-fix.md`（修复后补写）。*

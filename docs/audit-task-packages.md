# CN-JudBench 任务包与数据层审计

> 审计范围：`tasks/**`（9 包）+ `data/public/*.jsonl` + `src/cnjudbench/tools/gold/*` + `lawkb/**` + `scripts/build_min_lawkb.py`  
> 对照：`FRAMEWORK.md` v0.3.1（§4.2 适用面、§3.1 hcut、§6 任务包协议、附录 B/C/D、§12 伦理）  
> 方法：只读核对；用 `.venv` Python 3.13 跑 `validate_tasks` / `validate_items_dir` / lawkb `resolve_article` / 工具金样重算。  
> 官方校验结果：`TASK_ERRS=[]`、`ITEM_ERRS=[]`（下文问题多为**校验器未覆盖**或**语义/同源**问题）。

---

## 范围

| 层 | 路径 | 观察 |
|---|---|---|
| 任务包 | `tasks/{cit_validity,u_element_extract,s_charge_subsume,tool_search_statute,gaia_fee_deadline,contract_risk,a_irac_reason,tau_jud_intake,long_horizon_case}/` | 9 包均有 `task.yaml` + `predicates*.yaml` + `reference.md` + `README.md` |
| 题面 | `data/public/*.jsonl` | 87 题；**无** `data/holdout|live`（holdout 不入库符合 §9 L3/守卫，但 live 亦空） |
| 金样工具 | `src/cnjudbench/tools/gold/{fee,deadline,cases}.json` | 与 `fee/deadline/cases` 实现及 gaia/tool 题金样一致 |
| lawkb | `lawkb/laws/*.yaml` + `lawkb/text/*.txt`（由 `scripts/build_min_lawkb.py` 生成） | 6 部法律/解释；**缺**诉讼费用交纳办法、民诉、刑诉 |
| user_script | `tasks/tau_jud_intake/user_scripts/us-intake-01.yaml` | L3b 齐；gold 泄露检查通过 |
| rubric | 仅 `tasks/u_element_extract/rubric.yaml` | 其余主观包缺 |
| fewshot | 全库无 | FRAMEWORK §6 目录协议未落地 |

题量：cit 12 / u 10 / s 10 / tool 19 / gaia 10 / contract 8 / a 8 / tau 5 / long 5。

---

## 按包发现

### 1. cit_validity（横切 Cit · L1 · structured · 12 题）

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| P1 | `law_anchors` 与 gold `expect_status` 同源正确（12/12 经 `resolve_article` 一致），但包内 README 的「金样来源」未写清 `gold[]` 为**列表**且 `gold_path: "0.expect_status"` 依赖下标 0；多引用题一旦改成多元素列表会静默错判 | `tasks/cit_validity/predicates.yaml:11`、`data/public/cit_validity.jsonl` | 约定 gold 形状为单引用对象或明确 `gold_path` 规则；或改 `gold_path: "expect_status"` + gold 改对象 |
| P2 | `predicates_ref` 写成 `tasks/cit_validity/predicates.yaml`，无 FRAMEWORK 附录 C 示例的 `#id` 片段 | 全包 12 行 | 统一为 `…/predicates.yaml#cit-001` 或在规范中删掉片段要求 |
| P2 | cit-008 gold.article=`第264条`（测归一化）与 law_anchors.article=`264` 并存合理，但未在 README 标注「故意非规范条号」 | `data/public/cit_validity.jsonl:8` | README 标注 fixture 意图 |
| OK | 双/多 as_of 齐：2010/2014/2020/2020-09/2021/2024；应拒分列 `unknown_in_lawkb`/`unresolved_law`；`field_keep` 保 as_of | — | — |
| OK | 匹配层：`field(status)` exact + `on_fail: zero` 符合「判定结论一票否决」；未对自由文本 exact | `predicates.yaml:9-13` | — |

### 2. u_element_extract（U · L1 · extract · 10 题）

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| P1 | 有 `rubric.yaml`（`u_element_r1`）但 10 题 `rubric_id` 全为 `null`，Judge 链路不会挂上该 rubric | `data/public/u_element_extract.jsonl` 全部；`tasks/u_element_extract/rubric.yaml:2` | 题面写 `rubric_id: u_element_r1`，或 runner 按 task 默认加载 |
| P1 | rubric 含 `cite_quality`，但输出 schema 仅 `amount/date/case_no`，无 `citations`；主观项与机检面不一致 | `rubric.yaml:9-12` vs `task.yaml:10-11` | 删 cite 项，或输出增加引用字段 |
| P2 | 用 `deadline` 谓词判「关键日期」（履行/作案日）语义偏「期间届满」；矩阵虽允许，命名误导 | `predicates.yaml:6-8` | 增加 `date`/`field` 等值模式，或 README 声明借用 deadline=ISO 日相等 |
| OK | 金额 gold 为纯 int 元；日期 ISO；案号全角括号原样（`（2023）京0105民初1234号`）与 input 一致 | 全包 | — |
| OK | PTP `field_keep.case_no` 符合「已知事实不被改写」；无自由文本 PTP | `predicates.yaml:12-15` | — |

### 3. s_charge_subsume（S · L1 · structured · 10 题）

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| P2 | `field(path: charge)` 默认 exact 且 `on_fail: zero`：罪名枚举场景可接受，但同义罪名（如「盗窃」vs「盗窃罪」）会一票否决；与 elements 的 partial 策略不一致 | `predicates.yaml:3-6` | `match: labels`/去「罪」后缀归一，或白名单别名 |
| P2 | `statute on_fail: zero` 注释写「同法异条记 PASS 比例」——执行器对 partial 不触发 zero、仅 stale/未引 FAIL 才 zero，注释易误读 | `predicates.yaml:10-11`、`src/cnjudbench/predicates/ftp.py:96-97` | 注释改为「stale/未引 → FAIL+zero；同法异条 partial 不触发 zero」 |
| OK | 双版本罪名题齐：s-005（2016，253之一 → 侵犯公民个人信息罪）vs s-010（2014 → 出售、非法提供公民个人信息罪）；s-008（2010）vs s-001（2024）264 | jsonl | — |
| OK | PTP 禁引治安管理处罚法 + `field_keep.defendant_name`；中文「某」脱敏 | `predicates.yaml:15-21` | — |

### 4. tool_search_statute（R/U/G · L2 · tool_call · 19 题）

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| P1 | 12 题 `capability` 与 `task.yaml: capability: R` 不一致（t-dl/cf 为 U，t-ld 为 G） | `data/public/tool_search_statute.jsonl:10-18` | task 允许多维或题面对齐 R；taxonomy 聚合以题面为准并回写 task |
| P1 | `law_anchors` 大量 `unresolved_law`：诉讼费用交纳办法 / 民诉 / 刑诉 不在 lawkb；t-ss-001、t-sc-002 用民法典「第 1 条」占位 → `unknown_in_lawkb` | jsonl 各题 `law_anchors`；`scripts/build_min_lawkb.py` | lawkb 补三部法律常用条；占位条改为真实条或 `null` 锚点 |
| P2 | `predicates_lint.yaml` 用 `amount` 判 `answer.error_count`（计数≠金额） | `tasks/tool_search_statute/predicates_lint.yaml:6-8` | 用 `field` exact 数值或新增 `count` |
| P2 | t-fake-001 无 `predicates_ref`（靠默认 `predicates.yaml`），与「负例夹具」意图一致但可追溯性差 | jsonl:19 | 显式 `predicates_ref: …/predicates.yaml#t-fake-001` |
| OK | 与 `tools/gold/*.json` 同源：fee 50/2300/10、deadline 2024-06-17/2024-04-01/2024-04-23、cases fix-c-001/002/003/005；search_statute/get_article 金样 version_id 与 lawkb 一致 | 重算验证 | — |
| OK | 匹配层：终答 exact/amount/deadline/element@zero 合理；轨迹 PTP `tool_sequence`/`tool_ast` partial；`fake_tool` FTP zero | `predicates_*.yaml` | — |
| OK | 负例 t-fake-001（`negative: fake_tool`, `calls: []`）齐 | jsonl:19 | — |

### 5. gaia_fee_deadline（U/O/K · L3a · exact · 10 题）

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| P1 | g-03/g-04/g-06 `capability` 为 K/K/R，task 为 U | `data/public/gaia_fee_deadline.jsonl:3,4,6` | 同 tool 包：多维声明或回写 |
| P1 | 诉讼费/民诉/刑诉锚点 `unresolved_law`（g-01/02/05/07/08/09） | jsonl | lawkb 补录（同 tool 包） |
| P2 | g-04、g-06 缺 `predicates_ref`（落到默认 `field exact`） | jsonl:4,6 | 补 ref，避免默认集语义漂移 |
| OK | 金样与工具/算式同源：250000→5050、900000→12800、12000 离婚→300、利息 4800；deadline 2024-10-15/2024-06-17/2024-03-11 与 `calc_deadline` 一致 | `tools/gold/*` + 重算 | — |
| OK | **双 as_of 单题** g-06（2020-06-01 + 2021-06-01 → `not_yet_effective;ok`）齐 | jsonl:6 | — |
| OK | gold 不进 prompt（prompt 写明「gold 不会提供」）；progress 仅 diagnostic | `task.yaml:10-13`、`predicates_*.yaml` | — |

### 6. contract_risk（C/G · L1 · structured · 8 题）

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| P1 | **旧法题与禁引冲突**：c-008 `as_of=2009-05-13`，金样引用合同法解释（二）；但全包 PTP `must_not_statute: 中华人民共和国合同法`。正确援引当时《合同法》会被 cap_50 | `predicates.yaml:19-22`、jsonl c-008 | 按 as_of 例外：旧法题改用 `predicates_legacy.yaml`，或禁引表仅限 2021-01-01 后题 |
| P2 | FRAMEWORK 附录 A 写 `composite(["extract","gen"])`，落地为 `structured`（task 注释已解释 AND 矩阵挂不上 element） | `task.yaml:4,12-13`、`FRAMEWORK.md:514` | 改 FRAMEWORK 附录 A 与实现一致，或拆 components 段 |
| P2 | `risk_disclosure on_fail: zero` 与 a_irac/long 的 `flag` 不一致（同谓词不同红线） | `predicates.yaml:11-13` | 统一策略：缺披露 → cap_50；作结果保证 → zero |
| OK | `match: severity` 用于 `max_severity` 正确；risk_labels 用 element partial，无 exact 滥用 | `predicates.yaml:3-10` | — |
| OK | 多 as_of：2009/2021/2024；合成「某」脱敏；c-008 法名无书名号仍可 `lookup_law` 命中 | resolve 验证 | — |

### 7. a_irac_reason（A · L1 · structured · 8 题）

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| P1 | **金样法条错误**：a-007「免责条款效力」application 文义对应民法典 **506**，`rule_article`/citations/anchors 却写 **509** | `data/public/a_irac_reason.jsonl` a-007 | 改为 506（或 506+509 双锚），并同步 gold.rule_article |
| P1 | 应拒题 a-008 已有（`predicates_refuse.yaml`），但无「过度拒答」对偶负例（FRAMEWORK §1 Abst 双标签） | 全包 | 增 over_refuse 题 |
| P2 | 包级仅单一 as_of=2024-06-01，无双 as_of 配对 | 全包 | 补一组同争点双 as_of |
| P2 | README 缺污染/Verified/holdout 字段（FRAMEWORK §6） | `README.md` | 补齐 |
| OK | 长句 `contains`、条号 `article_set`、statute partial：匹配层修复后**无 exact 滥用** | `predicates.yaml:3-19` | — |
| OK | PTP 仅 `must_not_statute`（合同法）；无自由文本 PTP | `predicates.yaml:28-31` | — |
| OK | a-008 `source: synthetic_adversarial`、`hcut: [Abst,Proto]`、citations 空列表合理 | jsonl:8 | — |

### 8. tau_jud_intake（C · L3b · structured · 5 题）

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| P0 | **canary 跨文件撞车**：tj-001…005 与 long_horizon lh-01…05 共用 `CNJB-CANARY-abc000`…`abc004`，违反「每题 canary 唯一」（L0 防污染） | `data/public/tau_jud_intake.jsonl:1-5`、`data/public/long_horizon_case.jsonl:1-5` | 重发 canary；`validate_items_dir` 跨文件合并去重 |
| P1 | tj-001/tj-003 标 `hcut: Abst` 且 prompt「应拒须拒绝并转介」，但**无应拒题**；`refuse expect: answer` 对全部题要求「必须作答」 | `predicates.yaml:6-8`、jsonl tj-* | 增应拒题 + `predicates_refuse`；普通题保留 expect:answer |
| P1 | `state_goal` 不完整：tj-002…005 缺 `risk_note`，gold 有 → state F1 会漏计风险字段 | jsonl tj-002…005 | state_goal 与 gold 对齐（或显式声明子集） |
| P1 | 缺 `rubric.yaml`（Proto 六项检查单只在 description） | 包目录 | 按 FRAMEWORK §5.1 写 gate 清单 |
| P2 | `field_keep path: parties.0` 只锁第一当事人，过窄 | `predicates.yaml:15-17` | 对 parties 做集合 keep 或 state 覆盖 |
| OK | user_script personas+seeded_sample+user_seed；`assert_no_gold_leak` 通过 | `user_scripts/us-intake-01.yaml` | — |

### 9. long_horizon_case（U/O · L4 · structured · 5 题）

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| P0 | canary 与 tau 包重复（见上） | jsonl:1-5 | 同上 |
| P1 | 缺 `rubric.yaml`；score–time / 律师基线「未测」只在 description | 包目录、`task.yaml:10-11` | 补 rubric + limits/基线字段 |
| P2 | 单 as_of=2024-06-01；无双 as_of | 全包 | 补时点切片题 |
| P2 | README 缺许可/污染/Verified | `README.md` | 补齐 |
| OK | `match: severity`/`contains`/element partial；PTP 仅 must_not_statute；progress 进 diagnostic | `predicates.yaml` | — |
| OK | gold 含 `time_points` 供 AUC，未进 FTP（避免超纲） | jsonl | — |

---

## 跨包问题

| 级 | 发现 | 位置 | 修法 |
|---|---|---|---|
| **P0** | **canary 跨文件重复 5 对**（abc000–abc004）：tau ↔ long_horizon。`validate_items_file` 只在单文件内查重 | `data/public/tau_jud_intake.jsonl`、`long_horizon_case.jsonl`；`src/cnjudbench/validate/items.py:39-52` | 数据重发唯一 canary；校验器对全库 canary/id 合并去重 |
| **P1** | **lawkb 覆盖不足**：诉讼费用交纳办法、民诉、刑诉、民法典第 1 条等 anchors 无法 resolve（`unresolved_law`/`unknown_in_lawkb`），与「金样/lawkb 吥源」目标冲突；CiteGuard 会分列 unknown，但题面自称有效锚点 | `data/public/{gaia,tool}*.jsonl` anchors；`scripts/build_min_lawkb.py` | 扩 P0 最小库（附录 D.6）或改 anchors 为库内条文 |
| **P1** | **应拒/负例不齐**：仅 a-008（refuse）+ t-fake-001（fake_tool）；缺 over_refuse、over_promise、危险承诺对偶题；tau 标 Abst 无负例 | 全库 | 每含 Abst 包至少 1 应拒 + 1 过度拒答 |
| **P1** | **双 as_of 题面不足**：仅 g-06 单题双 as_of；a_irac/long/tau 全单点 as_of | 多包 | 每包至少 1 组双 as_of（或 README 说明不适用） |
| **P1** | **capability 题/task 不一致 12 题**（gaia 3 + tool 9） | 对应 jsonl / task.yaml | 统一标签源；校验器可 warn |
| **P1** | **rubric 覆盖不足**：仅 u 有 rubric 且题面未挂 `rubric_id`；A/C/L3b/L4 缺 | `tasks/*/` | 主观包补 rubric.yaml 并挂 id |
| **P2** | **FRAMEWORK 附录 B** 谓词类型表缺 `tool_sequence/tool_ast/fake_tool`（§4.2.1 矩阵已有） | `FRAMEWORK.md:522-526` vs `schemas/task.py:23-28` | 附录 B 补全三型 |
| **P2** | **composite 全库 0 题**；contract_risk 与附录 A 不一致（有注释） | FRAMEWORK 附录 A、题面 | 要么上 composite 样例，要么改文档 |
| **P2** | **fewshot/** 目录协议未落地（FRAMEWORK §6） | `tasks/*/` | 可选，但协议应标 optional |
| **P2** | `predicates_ref` 均无 `#item_id` 片段（附录 C 示例有） | 全库 | 统一格式 |
| **P2** | `hcut` 数组顺序不统一（`Abst,Proto` vs `Proto,Abst`） | a-008 / tj-001 / tj-003 | 规范排序或校验器排序输出 |
| **P2** | 匹配层：**exact 滥用已基本修复**——自由文本走 `contains`/`article_set`/`severity`；exact 仅保留 charge/status/answer 等短字段。残余风险是 **field 默认 exact** 对未写 `match` 的短文本仍偏严 | `predicates/ftp.py:154` | 文档写明默认 exact；标签类字段强制显式 match |
| **P2** | **on_fail 不一致**：`risk_disclosure` zero/flag 混用；`statute` zero（s）vs partial（a/c/lh）；`state` zero 偏严 | 各 predicates*.yaml | 出 on_fail 策略表，按红线/结构分档 |
| **P2** | **severity/article_set/contains 用法本身正确**，未见误用 | 多包 | — |
| OK | holdout 无入库 + `runner/guards.py` 拒读 | `data/`、guards | 符合 §9 |
| OK | 合成脱敏：姓名「某」、`synthetic*`、无身份证/账号 | 全库 | 符合 §12.2 |
| OK | 金额 int 元 / 日期 ISO / 案号原样全角；中文条号（第264条、253之一）有归一化覆盖 | u/cit/s | — |
| OK | tools/gold 与 gaia/tool 题、实现三方一致（fee/deadline/cases 重算全匹配） | — | — |
| OK | cit 12 题 expect_status 与 lawkb resolve 12/12 一致 | — | — |
| OK | user_script 无 gold 字面泄露 | us-intake-01 | — |
| OK | 全部 `status: draft`，未伪标 active | task.yaml | 符合状态机 |

---

## 摘要表

| 包 | 题数 | output_type | 完整性 | 金样/lawkb/tools 同源 | 应拒/负例 | 双 as_of | 最高级问题 |
|---|---:|---|---|---|---|---|---|
| cit_validity | 12 | structured | 齐（无 rubric 可接受） | **12/12 一致** | unknown/unresolved 分列 | 6 个 as_of | P2 gold_path 下标 |
| u_element_extract | 10 | extract | rubric 未挂 id | 金额/日期/案号自洽 | — | 弱 | P1 rubric_id/cite 项 |
| s_charge_subsume | 10 | structured | 齐 | 锚点可 resolve | 禁引负向 PTP | 7 个 as_of | P2 charge exact |
| tool_search_statute | 19 | tool_call | predicates_* 齐 | **tools/gold 一致**；anchors 缺口 | t-fake-001 | 4 个 as_of | P1 capability/lawkb |
| gaia_fee_deadline | 10 | exact | 2 题缺 ref | **fee/deadline 一致**；anchors 缺口 | — | **g-06** | P1 capability/lawkb |
| contract_risk | 8 | structured | 齐 | c-008 旧法 OK | — | 3 个 as_of | P1 禁引合同法 vs 旧法 |
| a_irac_reason | 8 | structured | refuse 分派齐 | **a-007 条号错** | a-008 | 否 | P1 金样 509≠506 |
| tau_jud_intake | 5 | structured | user_script 齐；缺 rubric | state_goal 缺字段 | **缺应拒** | 否 | **P0 canary** |
| long_horizon_case | 5 | structured | 缺 rubric | time_points 合理 | — | 否 | **P0 canary** |

### 修复优先级建议

1. **P0**：重发 5 个 canary + 校验器跨文件唯一性。  
2. **P1**：修 a-007 条号；lawkb 补诉讼费/民诉/刑诉；contract 旧法禁引例外；tau 应拒题 + state_goal 对齐；capability 对齐；主观包 rubric + `rubric_id`。  
3. **P2**：on_fail 策略表、FRAMEWORK 附录 B/composite、predicates_ref 片段、lint 的 amount→count、README 四件套字段。

---

*本审计只读完成，未改任务包/数据/源码；仅新增本报告。*

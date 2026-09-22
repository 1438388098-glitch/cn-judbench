# CN-JudBench 评分/匹配层深度审计报告

> 审计方式：只读静态审计（含未提交工作区 diff 对照）。未改任何源码。
> 权威库：`D:\Claudeworkspace\cn-judbench`
> 对照规范：`FRAMEWORK.md` §0 评分总则 / §3.1 横切红线 / §4 谓词 / §8.1 计算顺序 / 附录 D

---

## 范围

| 模块 | 路径 | 状态 |
|---|---|---|
| 归一化/松匹配 | `src/cnjudbench/score/norm.py`、`score/__init__.py` | **未提交（untracked）** |
| FTP/PTP/工具谓词 | `src/cnjudbench/predicates/{ftp,ptp,tools,base,registry}.py` | ftp/ptp **有未提交改动** |
| 法条解析 | `src/cnjudbench/lawkb/resolve.py` | **有未提交改动** |
| CiteGuard | `src/cnjudbench/citeguard/{check,extract}.py` | check **有未提交改动** |
| 单题判分 | `src/cnjudbench/runner/evaluate.py` | **有未提交改动** |
| 终态 F1 | `src/cnjudbench/dialog/state_score.py` | **有未提交改动** |
| 指标层 | `src/cnjudbench/metrics/{aggregate,bootstrap,cost,stability,variance}.py` | 已提交 |
| 关联（交叉验证） | `scale.py`、`gates/redline.py`、`judge/*`、`tests/test_score_norm.py` 等 | 交叉引用 |

未提交相关改动（评分链）：`score/`（新增）、`lawkb/resolve.py`、`predicates/ftp.py`、`predicates/ptp.py`、`runner/evaluate.py`、`citeguard/check.py`、`dialog/state_score.py`、`tests/test_score_norm.py`、四份 `tasks/*/predicates.yaml`。

---

## 发现

### P0 — 会直接导致错分/漏判主路径

#### P0-1 法名解析双双失败时 `None == None` 误判为同法
- **文件:行**：`src/cnjudbench/predicates/ftp.py:75-76`
- **问题**：
  ```python
  anchor_law_id = ctx.store.alias.get(normalize_law_name(anchor.law))
  claim_law_id = ctx.store.alias.get(normalize_law_name(c.law_raw))
  if claim_law_id != anchor_law_id:
      continue
  ```
  锚点法名与模型引用法名**都未命中别名表**时，二者均为 `None`，`None != None` 为假，后续条号比较继续执行。两个毫不相关的未入库法（如金样「民法典」vs 模型「某条例」）会被当成同一部法，配合同法异条逻辑可能给出 `PASS` + `×0.5` 甚至 `hit_exact`。
- **影响**：statute 覆盖虚高；`same_law_other` 语义被污染；与 CiteGuard「unresolved_law 不得猜简称」原则冲突。
- **建议修法**：比较前显式要求双方均解析成功：
  ```python
  if anchor_law_id is None or claim_law_id is None or claim_law_id != anchor_law_id:
      continue
  ```
  或改比较归一化法名字符串，并对 `anchor_law_id is None` 记数据错误拒判。

#### P0-2 `claim_extract_miss` 降级却给满分 `1.0`，污染 FTP 基数
- **文件:行**：`src/cnjudbench/predicates/ftp.py:60-64`（statute）、`ftp.py:215-217`（no_fabrication）；合成入口 `predicates/registry.py:76-78`
- **问题**：gen 抽不到 claim 时返回 `PredicateResult(..., True, 1.0, ...)`。`compose_score` 的基数是「非 flag 谓词的 `pass_ratio` 均值 ×100」，`passed=True` 且 `pass_ratio=1.0` 会**计入并拉满基数**。FRAMEWORK §4.2 要求「降级为 rubric gate，不得对原文做脆弱正则」——正确语义是**本条不机判/不进基数**，不是「机检判过」。
- **影响**：自由文本完全无引用时，statute + no_fabrication 双双满分；若其余谓词为 flag/partial，题分可虚高至接近 100。违反「缺评 n/a 禁止用分数充数」的评分总则精神。
- **建议修法**：降级结果不进 `scored` 基数——增加 `skipped` 标志，或强制 `on_fail` 语义为 `flag` 且 `pass_ratio` 不参与均值；题级若有 rubric gate 再单独处置。金样测试 `test_statute_gen_degrades...` 目前断言 `gen_r[0].passed`，应一并改为断言「跳过/不计分」。

---

### P1 — 正确性/一致性/稳健性缺陷

#### P1-1 `field` 的 `match: exact` 仍走 `labels_match` 松匹配，与注释承诺相反
- **文件:行**：`src/cnjudbench/predicates/ftp.py:139-141`（注释）、`ftp.py:171-175`（实现）
- **问题**：文档写明「默认 exact，松匹配必须显式声明，防放水」，但 else 分支实现为：
  ```python
  ok = got is not None and (str(got).strip() in accepted or labels_match(got, want))
  ```
  `labels_match` 含双向子串 + `text_coverage>=0.55` 回退，等于 exact 模式自动放水。
- **建议修法**：`exact` 分支只做 `str(got).strip() in accepted`；包含/同义必须走 `contains` / `severity` / 显式 `aliases`。补金样：want=`合同有效`、got=`合同无效` 等负例在 exact 下必须 FAIL。

#### P1-2 中文条号转换仅支持到「百」，民法典千位条号失配
- **文件:行**：`src/cnjudbench/lawkb/resolve.py:60-87`（`_cn_article_to_int`）
- **问题**：注释写明「至百位」。`《民法典》第一千二百六十条` 含「千」，遇未知字符直接 `return s + suffix`，得到 `"一千二百六十"` 而非 `"1260"`。`article_set` / statute 条号比对、lawkb `by_key` 查找会全部 miss。
- **影响**：民法典（1260 条）、民诉法等条号 ≥1000 的匹配系统性失效；与用户约定「第二百六十四条→264」同属一链，264 没问题、1260 有问题。
- **建议修法**：补「千/万」权位（或改用结构化中文数字解析）；单测覆盖 `第一千零一条→1001`、`第一千二百六十条→1260`、`第1260条→1260`。

#### P1-3 stale / wrong_vintage 未强制 `0.00`（依赖任务包 on_fail，partial 时可漏）
- **文件:行**：`predicates/ftp.py:85-108`、`predicates/registry.py:81-106`、FRAMEWORK §3.1:98、DoD 测试 `tests/test_e2e_mock_smoke.py:67-82`
- **问题**：
  1. FRAMEWORK §3.1 写「错误时效 → 本题 ×0.50」，DoD/用户清单写「stale/wrong_vintage 必须 0.00」。规范内部不一致，实现跟的是**任务包 `on_fail`**。
  2. `s_charge_subsume` 的 statute 为 `on_fail: zero`，stale → 0.00（与 DoD 一致）。
  3. 但 `a_irac_reason` / `contract_risk` / `long_horizon_case` 的 statute 为 `on_fail: partial`，stale 仅 `passed=False`、`pass_ratio` 进均值，**既非 0.00 也非 ×0.50**。
  4. `compose_score` 对 `stale_statute` / `wrong_vintage` **无一票否决钩子**。
- **建议修法**：在 `compose_score` 写死：taxonomy 含 `stale_statute`（或 resolve 为 `wrong_vintage`/`not_yet_effective`）→ `final = 0.00`（若框架最终采纳 ×0.50，则写死 ×0.50 并改 DoD）。不要把「时效错误处置」下放给任务包默认值。同步修订 FRAMEWORK §3.1 与 §8.1 措辞一致。

#### P1-4 同法异条 PASS 时 `failure_taxonomy` 被 `compose_score` 丢弃
- **文件:行**：`predicates/ftp.py:100-112`、`predicates/registry.py:82-84`
- **问题**：同法异条路径 `passed=True, ratio=0.5, taxonomy="wrong_article"`，但
  ```python
  for r in ftp_results:
      if r.passed:
          continue  # taxonomy 不收集
  ```
  ItemResult.taxonomy 不会出现 `wrong_article`，报表漏失败归因。且 `PredicateResult` 文档约定「`failure_taxonomy` 仅失败时非空」，此处 PASS 也带 taxonomy，契约被破坏。
- **建议修法**：`compose_score` 对 `passed` 但 `failure_taxonomy` 非空的结果仍并入 taxonomy（或拆 `note_taxonomy`）；statute 同法异条在 detail 中已写，taxonomy 列也须可机读。

#### P1-5 FRAMEWORK Hall 题级「每处 −20.00」未实现
- **文件:行**：FRAMEWORK §3.1:100、§8.1:330-331；实现仅见 `gates/redline.py:27-38` 与 `registry.py:70-107`
- **问题**：§8.1 强制计算顺序 ② 要求 `Hall 每处 −20.00 分/题，下限 0.00`。当前 `fabricated_case` 走的是 `on_fail=zero` 一票否决或 `no_fabrication` 0/1，**没有「每处 −20」的题级累进扣分**。`redline_multiplier`（§8.1 ⑤）同样未落地。
- **建议修法**：在 item_score 阶段实现 Hall 计数×20 扣分后再进 gate；或在 FRAMEWORK 明确 v0.3.1 已取消 −20 而只保留 gate，避免评测口径双轨。

#### P1-6 `state_f1`：want 为空列表/空串而 got 非空 → 字段记 0.0
- **文件:行**：`src/cnjudbench/dialog/state_score.py:33-41`；依赖 `score/norm.py:107-116`（`set_f1` 对空 want 返回 `(0.0,0,0)`）
- **问题**：
  ```python
  f1, tp, n_want = set_f1(g_list, w_list)
  if n_want == 0 and not g_list:  # 仅双空才给 1.0
      matched...
      continue
  field_f1s.append(f1)  # want 空、got 非空 → 0.0
  ```
  「金样未要求该字段」被当成未命中，错误拉低 F1。`_as_list("")` 还会把空字符串变成 `[""]`，在 `set_f1` 中**永不可命中**（`labels_match(g, "")==False`）。
- **建议修法**：`n_want == 0` 一律视为该字段无可比目标（1.0 或跳过，与 empty goal 口径一致）；过滤 `want/got` 中的空白元素。

#### P1-7 `element` 在 gold 无可比要件时记 FAIL 0.0（应用 n/a / 拒判）
- **文件:行**：`src/cnjudbench/predicates/ftp.py:128-130`
- **问题**：金样配置错误（`gold 无可比要件`）被归因为模型 `element_miss` 且 `pass_ratio=0.0`。评分总则「不可评记 null/n/a，禁止填 0.00 充数」——这是**不可评**，却填了 0。
- **建议修法**：抛 `PredicateError`（拒判 n/a）或返回 `score=None` 链路；至少不要打 `element_miss`。

#### P1-8 谓词实现抛出非 `PredicateError` 会崩整卷
- **文件:行**：`src/cnjudbench/runner/evaluate.py:203-208`（仅捕获 `PredicateError`）
- **问题**：如 `float(extra.get("tolerance", 0))` 遇 `tolerance: null` 抛 `TypeError`；`extra.get("aliases", {})` 若任务包误写成列表则 `.get` 抛 `AttributeError`。异常穿透 `evaluate_item` → `run_task`，**整卷中断**而非单题 n/a。
- **建议修法**：`except PredicateError` 外再兜 `except Exception` → `score=None` + `error=repr(e)`（保持「拒判 n/a」）；任务包加载期用 pydantic 收紧 `tolerance/aliases` 类型。

#### P1-9 `fake_tool` 未校验「期望工具是否真的被调成功」
- **文件:行**：`src/cnjudbench/predicates/tools.py:33-34`
- **问题**：
  ```python
  if expected and not executed:  # executed = 任意成功日志
      violations.append(...)
  ```
  期望 `[fee]` 却只成功调用 `deadline` 时，`executed` 非空 → **不记 fake_tool**。假调用/错调用漏检。
- **建议修法**：改为 `if expected and not (set(expected) & {e.name for e in executed})` 或与 `tool_sequence` 共用覆盖判断；补负例金样「调错工具」。

#### P1-10 路径穿越：`predicates_ref` 与 `item_id` 落盘文件名
- **文件:行**：`src/cnjudbench/runner/evaluate.py:239`、`src/cnjudbench/runner/manifest.py:114-116`
- **问题**：
  1. `for cand in (Path(ref), task_dir / ref, ...)` —— `ref` 可为 `../../secrets/foo.yaml` 或绝对路径（pathlib 拼接遇绝对路径会替换根），可把**任意 YAML** 加载为谓词集。
  2. `(items_dir / f"{item_id}.trajectory.json").write_text(...)` —— `item_id` 含 `../` 或 `..\\` 时写到 out_dir 之外。
- **影响**：本地评测框架、数据多为可信；但 holdout/jsonl 若来自第三方或混合来源，存在任意文件读（进谓词）与任意路径写。
- **建议修法**：`ref` 限制在 `task_dir.resolve()` 之下（`Path.resolve().is_relative_to(task_dir.resolve())`）；`item_id` 写盘前 `re.sub(r"[^\w.-]", "_", item_id)` 或仅用 hash 文件名。

#### P1-11 测试夹具 as_of 回落与 evaluate 实现不一致（未提交改动自洽缺口）
- **文件:行**：`src/cnjudbench/runner/evaluate.py:166-177`（ISO 校验后回落题面）vs `tests/test_predicates_ftp_ptp.py:47-49`（`c.as_of or item.as_of`，非 ISO 叙述会传入）
- **问题**：evaluate 侧已修「2014年案发时…」不再拖垮整卷；单测 `mk_ctx` 仍是旧行为。单测路径与生产路径语义分叉，回归保护失效。
- **建议修法**：抽出 `effective_as_of(claim, item)` 供 evaluate 与测试共用；补 claim.as_of 为中文叙述的单测。

---

### P2 — 质量/边界/文档一致性

#### P2-1 `article_set` 分支死代码，条件无意义
- **文件:行**：`src/cnjudbench/score/norm.py:58-62`
- **问题**：`if n and n not in ("", s): out.add(n) elif n: out.add(n)` 两分支等价于 `if n: out.add(n)`；且比较对象 `s` 是整串而非 `part`。不影响结果，妨碍阅读与审计。

#### P2-2 `KEY_ALIASES` 中「案件类型」双挂 `matter_type` 与 `issue`
- **文件:行**：`src/cnjudbench/score/norm.py:142, 148`
- **问题**：`find_key` 顺序敏感，同一中文键可能取错字段，终态 F1/字段命中错位。
- **建议修法**：去掉 `issue` 侧的「案件类型」，或改为「争点/争议焦点」独占。

#### P2-3 `field_keep.expect_from` 只识别 `item.as_of`，测试用法无效但碰巧通过
- **文件:行**：`src/cnjudbench/predicates/ptp.py:46-51`；`tests/test_predicates_ftp_ptp.py:217-218`
- **问题**：测试写 `expect_from: "gold.case_no"`，实现只分支 `item.as_of`，否则走 `expect_path|path` 对 gold 取值。语义与任务包作者预期可能不符。

#### P2-4 `no_fabrication` 主键形态正则过宽/过窄
- **文件:行**：`src/cnjudbench/predicates/ftp.py:228`
- **问题**：`r"[a-z][a-z0-9_]{2,}"` 匹配任意短 snake_case（如 `abc`），不匹配大写 `CL_264_2011`。与「仅库主键形态」意图之间缺少与 lawkb `version_id` 模式的对齐（建议改为与库内 version_id 同构的强模式，或 `vid in store.all_version_ids()` 再判矛盾）。

#### P2-5 `set_f1` / `labels_match` 子串过松的数值边界
- **文件:行**：`src/cnjudbench/score/norm.py:78-91`
- **问题**：`"264" in "2640"` 为真；短数字串当 label 时可能误命中。条号场景应强制走 `article_set`。

#### P2-6 `text_coverage` 阈值 0.55 无配置/无校准说明
- **文件:行**：`src/cnjudbench/score/norm.py:91, 104`；`ftp.py:169`
- **问题**：二字组覆盖率阈值写死 0.55，长句改写下召回/精度未在 FRAMEWORK 锚定；建议进任务包可配并出诊断分布。

#### P2-7 `TaskRun.mean` 静默丢弃 n/a 题，可能抬高均值
- **文件:行**：`src/cnjudbench/runner/evaluate.py:55-58`
- **问题**：符合「禁止 0 充数」，但 macro 均值分母只含可评题。建议报表强制同时输出 `n/n_a`（部分 CLI 已有 n），并在 FRAMEWORK 写明分母口径。

#### P2-8 `as_of_used` 记录的是 claim 原始字符串而非生效 as_of
- **文件:行**：`src/cnjudbench/runner/evaluate.py:179-181`
- **问题**：非 ISO 的 `c.as_of` 仍进 manifest 的 `as_of_used`，与实际用于 resolve 的日期不一致（生效日已回落题面）。manifest 可复现性字段被污染。

#### P2-9 读入编码固定 `utf-8`，不剥 BOM
- **文件:行**：多处 `read_text(encoding="utf-8")`（`evaluate.py:72-75` 等）
- **问题**：Windows 编辑器带 BOM 的 YAML/JSONL 会使首键带 `\ufeff` 或 `json.loads` 失败 → 单题/整包崩溃（结合 P1-8 更脆）。建议 `encoding="utf-8-sig"`。

#### P2-10 `state_score.py` 使用 `__import__("cnjudbench.score.norm", ...)`
- **文件:行**：`src/cnjudbench/dialog/state_score.py:47-50`
- **问题**：非常规导入，静态扫描易误报动态导入；功能正确。应改为顶部 `from ..score.norm import KEY_ALIASES`。

#### P2-11 `norm.py` 重复定义 `_WS`
- **文件:行**：`src/cnjudbench/score/norm.py:18` 与 `:70`

#### P2-12 `pass_at_k` 只看前 k 次、不足 k 跳过
- **文件:行**：`src/cnjudbench/metrics/cost.py:11-17`
- **问题**：与组合意义的 pass^k（任取 k 次全过）不同；文档写「前 k 次全过」尚可接受，但 FRAMEWORK §8.2 的 pass^k 语义应在报告脚注固定，避免横向对比误读。分母 `or 1` 在无有效 runs 时返回 0.0 而非 n/a。

#### P2-13 `diagnostic_drop` 不接受 None
- **文件:行**：`src/cnjudbench/metrics/aggregate.py:25-28`
- **问题**：主集/诊断任一为 None 时抛 TypeError；应返回 n/a。

#### P2-14 `fmt2` 对 NaN/Inf 未防护
- **文件:行**：`src/cnjudbench/scale.py:39-41`
- **问题**：`Decimal("nan")` 行为依赖版本；建议显式拒绝非有限值。

---

## 不是问题但需确认

| # | 观察 | 说明 |
|---|---|---|
| C1 | 同法异条 `PASS ×0.5`（进基数、不触发 zero） | 与用户清单「同法异条 PASS×0.5」一致（`ftp.py:96-101`）。但须确认：`on_fail: zero` 的 statute 下，同法异条**故意不**一票否决是否仍为产品意图（注释已写明）。 |
| C2 | severity「中高→high」 | `score/norm.py:21` 实现正确；须确认「重大/严重」→high、「一般/普通」→medium 的司法语感是否被 rubric 作者接受。 |
| C3 | contains = want 二字组在 got 中覆盖率 | `text_coverage` 实现符合；阈值 0.55 见 P2-6。 |
| C4 | element 非独占包含（一句话含多要件） | `set_f1` 任一 got 命中即计，precision 用 `min(1, tp/\|got\|)` 防长句刷分，符合复盘约定。 |
| C5 | no_fabrication 仅库主键形态才记幻觉 | 与 impl 注释及 unknown 分列原则一致；叙述性标签不记 `fabricated_case` 是有意为之（P2-4 是模式强弱问题）。 |
| C6 | `labels_match` 双向包含 | 刻意松匹配（真实中文标签更长/更短）；exact 模式误接松匹配才是问题（P1-1）。 |
| C7 | `state_f1({}, {}) → f1=1.0` | 测试锁定；空金样给满分 vs「缺评 n/a」张力，属产品口径（当前 τ-Jud 空 goal 表示无终态约束）。 |
| C8 | 机检分与 Judge 分平行展示、`combine(parallel)` 不合并 | 符合戒律 3「绝不与机检混成一个数」。 |
| C9 | `yaml.safe_load` / 无 `eval`/`exec` 用户输入 | 除 `__import__` 固定模块名外，未见代码注入面；`subprocess` 仅 `git rev-parse` 固定参数。 |
| C10 | API Key 只进环境变量/内存，缓存只落盘 completion 文本 | `adapters/cache.py` 未写密钥；`openai_compat.py` 头不落盘。**不是**密钥落盘问题。 |
| C11 | 未提交 `score/` + 多文件同时改 | 模块间引用（norm → resolve 的 `normalize_article_no`，ftp/ptp/state_score → norm）自洽；**必须与 `tests/test_score_norm.py` 同提交**，否则 CI 缺金样。 |
| C12 | 规范冲突：FRAMEWORK「错误时效 ×0.50」vs DoD「wrong_vintage → 0.00」 | 实现跟任务包 on_fail，已开 P1-3；产品需二选一并改规范文本。 |

---

## 摘要表

| ID | 严重级 | 位置（主） | 一句话 | 建议 |
|---|---|---|---|---|
| P0-1 | P0 | ftp.py:75-76 | 法名双失败时 None==None 误匹配 | 显式要求 law_id 非空再比 |
| P0-2 | P0 | ftp.py:63-64,216-217 | claim_extract_miss 却记 1.0 进基数 | 降级 = 跳过计分，非 PASS |
| P1-1 | P1 | ftp.py:171-175 | exact 仍 labels_match 松匹配 | exact 只比别名表 |
| P1-2 | P1 | resolve.py:60-87 | 中文条号无「千」位，民法典≥1000 失配 | 扩展权位 + 金样 |
| P1-3 | P1 | registry.py / ftp statute | stale/wrong_vintage 未强制 0.00 | compose_score 写死处置 |
| P1-4 | P1 | registry.py:82-84 | 同法异条 PASS 的 taxonomy 被丢 | passed 也收集 taxonomy |
| P1-5 | P1 | 全链路缺 Hall−20 | FRAMEWORK §8.1 未实现 | 实现或改规范 |
| P1-6 | P1 | state_score.py:33-41 | 空 want + 有 got → 0.0 | 无可比目标记 1.0/跳过 |
| P1-7 | P1 | ftp.py:128-130 | gold 空要件记 FAIL 0 | 拒判 n/a |
| P1-8 | P1 | evaluate.py:203-208 | 非 PredicateError 崩卷 | 单题兜底 n/a |
| P1-9 | P1 | tools.py:33-34 | fake_tool 不查期望工具是否被调 | 比对 expected∩executed |
| P1-10 | P1 | evaluate.py:239 / manifest.py:115 | predicates_ref、item_id 路径穿越 | resolve 后缀约束/白名单文件名 |
| P1-11 | P1 | tests vs evaluate as_of | 测试与生产 as_of 回落分叉 | 共用 effective_as_of |
| P2-1…14 | P2 | 见上 | 死代码/别名冲突/BOM/均值分母/pass^k 等 | 见各条 |

### 与 FRAMEWORK 评分总则对照（结论）

| 规则 | 结论 | 依据 |
|---|---|---|
| 百分制 0.00–100.00 | **基本符合** | `to_percent_*`、FTP 均值×100、PTP 乘法链 |
| 两位小数 ROUND_HALF_EVEN | **符合** | `scale.fmt2` 使用 `ROUND_HALF_EVEN`；排序用未舍入分 |
| 缺评 n/a 禁止 0 充数 | **部分违反** | 主路径 ItemResult `None→n/a` 正确；P0-2 用 1.0 充数、P1-7 用 0.0 充数 |
| stale/wrong_vintage → 0.00 | **部分违反** | 仅 `on_fail: zero` 时成立；见 P1-3；且与 FRAMEWORK「×0.50」冲突 |
| gate 一票否决（zero 优先于 cap） | **符合** | `compose_score:105-106`、`apply_gates:19-20` |
| 同法异条 PASS×0.5 | **实现一致** | `ftp.py:90-101`；taxonomy 丢失见 P1-4 |
| 中文条号→阿拉伯 | **部分符合** | 至百位正确（第二百六十四→264）；千位见 P1-2 |
| element 非独占包含 | **符合** | `set_f1` |
| contains 二字组覆盖率 | **符合** | `text_coverage`；阈值需确认 |
| severity 中高→high | **符合** | `SEVERITY_MAP` |
| no_fabrication 仅库主键形态 | **符合** | `re.fullmatch(r"[a-z][a-z0-9_]{2,}", vid)` |

### 未提交改动自洽性（结论）

| 链路 | 结论 |
|---|---|
| `score/norm` ← ftp/ptp/state_score 引用 | **自洽**（导入名与 `__all__` 覆盖实际使用；`text_coverage`/`KEY_ALIASES` 经模块路径导入） |
| `resolve.normalize_article_no` ← `article_set` / statute | **自洽**（中文数字链路新加，单测 `test_score_norm`/`test_cn_article_normalize` 已锁 264/253之一） |
| `evaluate._as_of_for` ←→ `citeguard.check` bad_as_of | **生产路径自洽**；与单测 mk_ctx **不自洽**（P1-11） |
| `no_fabrication` 正则 ←→ DoD 测试 `" hallucinated_v1"` | **自洽**（strip 后命中 snake_case） |
| 四份 `tasks/*/predicates.yaml` 新 match 模式 ←→ `field()` | **自洽**（contains/severity/article_set 分支存在） |
| 提交卫生 | **风险**：`score/` 与 `tests/test_score_norm.py` 仍为 untracked，若只 commit 改过的 py 会导致 import 失败；须同一逻辑提交引入 |

### 安全/稳健（结论）

| 项 | 结论 |
|---|---|
| 路径穿越 | **有问题**（P1-10） |
| eval/exec | **未发现**用户可控动态执行（仅固定 `__import__`） |
| 密钥落盘 | **未发现**（env/内存；缓存不含 key） |
| Unicode/BOM | **薄弱**（`utf-8` 不剥 BOM，P2-9） |
| YAML | `safe_load`，安全 |
| 异常吞掉 | 反向问题：**吞得不够**导致崩卷（P1-8）；cache/OSError 静默可接受 |

---

*报告生成：只读审计。修复优先级建议：P0-1/P0-2 → P1-3/P1-1/P1-8 → 其余 P1 → P2。*

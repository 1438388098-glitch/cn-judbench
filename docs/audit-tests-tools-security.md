# CN-JudBench 测试 / 工具 / CLI / 安全层审计

> 范围只读审计；不改源码。复测环境：`D:\Claudeworkspace\cn-judbench\.venv`（Python 3.13，`python -m pytest -q` → **182 passed**）。

## 范围

| 维度 | 覆盖对象 |
|---|---|
| 测试 | `tests/**`（32 个 `test_*.py` + `conftest.py`） |
| 工具沙箱 | `src/cnjudbench/tools/**`（sandbox / 6 工具 / gold / schema） |
| 适配器 | `src/cnjudbench/adapters/**`（mock / openai_compat / cache / base） |
| CLI / 入口 | `src/cnjudbench/cli.py`、`src/cnjudbench/__main__.py` |
| Runner | `src/cnjudbench/runner/**`（evaluate 签名与调用约定；evaluate 内部细节从略） |
| 打包与文档 | `pyproject.toml`、`README.md`、`FRAMEWORK.md` §4.2/§5/§7.1 合规抽查 |
| 泄露面 | 仓库根与 `reports/**` 的密钥 / 绝对路径 / BOM |

不在范围：`app.js` / `index.html` / `styles.css`（可视化面板，非本任务缺陷）；Judge 语义内部；lawkb 条文内容真实性。

---

## 发现

### P0（评测正确性或可被模型侧滥用）

#### P0-1 `tool_ast` 把业务失败算成「参数 AST 非法」

- **位置**：`src/cnjudbench/predicates/tools.py:77-78`（`valid = sum(1 for e in ctx.tool_log if e.ok)`）
- **证据**：沙箱 `ok` 表示**整次执行成功**，含业务 `tool_error`（如 `amount=-1`）与 `TypeError`（多余 kwargs 未在 `ARG_SCHEMAS` 拦截，落到 `impl(**args)`）。实测：`calc_fee(amount=-1)` + 合法调用 → `tool_ast ratio=0.5`，detail 写「参数合法 1/2，违例 calc_fee(tool_error: amount 必须为正)」——但该次 **schema 是过的**。
- **影响**：FRAMEWORK §4.2 明文 `tool_ast` =「参数 schema 合法率」。当前把值域/实现错误混入 AST 分，partial 乘法链会误伤正确参数轨迹。
- **修法**：
  1. `ToolLogEntry` 增加 `schema_ok: bool`（仅 `arg_schema`/`unknown_tool` 前置检查决定）；
  2. `tool_ast` 只统计 `schema_ok`；
  3. 多余 kwargs 在 `sandbox.execute` 里按 schema 拒绝（记 `arg_schema`），禁止穿透到 `impl(**args)`；
  4. 补负例：业务错误但 schema 合法 → `tool_ast=1.0`；多余 kwargs → `schema_ok=False`。

#### P0-2 `tool_sequence` 用 `e.ok` 当「是否调用过」

- **位置**：`src/cnjudbench/predicates/tools.py:58-61`
- **证据**：仅一次「名对参错」的 `calc_fee` → `tool_sequence` 报「工具覆盖 0/1，缺 [calc_fee]」（`tool_miss`），而按定义应是**已调用但参数非法**（`tool_arg_invalid`）。
- **影响**：taxonomy 错位（`tool_miss` vs `tool_arg_invalid`）；与 `tool_ast` 双重扣分时无法归因；假调用率与参数错误率不可分离。
- **修法**：覆盖集合改为 `{e.name for e in log}`（或 `schema_ok or name==expected`）；`tool_ast` 独管参数。与 P0-1 同一补丁组。

#### P0-3 `lint_document` 的 `doc_type` 路径穿越（模型可控）

- **位置**：`src/cnjudbench/tools/lint_doc.py:22-23`（`SCHEMA_DIR / f"{doc_type}.json"`）
- **证据**：`_load_schema('../gold/cases')` **成功**读入 `tools/gold/cases.json`（6 条）。沙箱把该参数原样交给工具，评测轨迹中的模型输出可驱动任意 `**/*.json` 读取（限 `.json` 后缀，但仍越出 schema 目录）。
- **影响**：沙箱纪律「禁外网、禁子进程」被本地任意 JSON 读取绕过一截；轨迹/错误信息可泄露仓库内其它夹具结构。
- **修法**：`doc_type` 白名单（仅 `SCHEMA_DIR.glob('*.json')` 的 stem）；或 `path.resolve()` 后断言 `path.is_relative_to(SCHEMA_DIR.resolve())`。补 `doc_type='../gold/cases'` 必失败测试。

#### P0-4 `write_run` 轨迹文件名 `item_id` 路径注入

- **位置**：`src/cnjudbench/runner/manifest.py:115`（`items_dir / f"{item_id}.trajectory.json"`）
- **证据**：`trajectories={'../evil': …}` → 写出 `run/evil.trajectory.json`（逃出 `items/`）。恶意/污染题面 `id` 含 `..` 或绝对路径片段时可写到 out 目录树外（取决于 OS 规范化）。
- **影响**：评测产物落盘位置不可信；与 holdout 守卫（只查路径段 `holdout`）叠加后，仍缺对 `item_id` 的字符集约束。
- **修法**：落盘前 `re.fullmatch(r'[A-Za-z0-9._-]+', item_id)`，非法则 sanitize/拒绝；schema 层同步约束 `Item.id`。

#### P0-5 `predicates_ref` 可读任意本机路径

- **位置**：`src/cnjudbench/runner/evaluate.py:239`（`for cand in (Path(ref), task_dir / ref, …)`）
- **证据**：首个候选 `Path(ref)` 对绝对路径直接 `is_file()`——实测 `C:\Windows\win.ini` 为 True。题面 `predicates_ref` 若被污染，可把任意文件当 YAML 读入谓词集（`yaml.safe_load` 降低 RCE 面，但仍可读密钥文件并进错误信息/拒判 detail）。
- **影响**：与「holdout 永不入 prompt」同级的数据边界问题；绝对路径/`..` 未拒绝。
- **修法**：只允许相对路径且 resolve 后落在 `tasks_root` 内；禁止绝对路径与 `..` 段。

---

### P1（合规 / 可维护性 / 边界正确性）

#### P1-1 `_type_ok` 把 `bool` 当作 `int`

- **位置**：`src/cnjudbench/tools/sandbox.py:90-94`
- **证据**：`_type_ok(True, int) is True`；`calc_deadline(start=…, days=True)` → `days=1` 成功。
- **修法**：`isinstance(v, bool)` 一律 False（对 int/float）。

#### P1-2 FRAMEWORK §7.1 Manifest 必填项缺口

- **位置**：`src/cnjudbench/runner/manifest.py:39-90`；对照 `FRAMEWORK.md:280-299`
- **缺口**：
  1. **无 `user_seed` / `model_seed`**（§7.1 示例块要求；仅 `run-dialog` 手写 manifest 有，且见 P1-3）；
  2. **无「每题 content hash」**——只有聚合 `dataset.item_content_hash`（整文件排序拼接 hash）；
  3. **无依赖 lock**（§7.1「依赖 lock」；仓库亦无 `requirements.txt` / lockfile，仅 `pyproject.toml`）；
  4. `judge` 块仅 `judge_calls/tokens` 进 accounting，缺 `judge.model_id / prompt_hash / mode` 结构化字段。
- **修法**：`build_manifest` 增补 `user_seed/model_seed`、`dataset.item_hashes: {id: sha256}`、`deps: {pydantic: …}` 或 lock 文件 hash、`judge: {...}`；测试同步断言。

#### P1-3 `run-dialog` 手写 manifest 缺 harness / prompt / lawkb 完整性字段

- **位置**：`src/cnjudbench/cli.py:528-543`
- **证据**：源码无 `harness_sha` / `prompt_hash` / `store_version` / `slice_union_hash`。
- **修法**：复用 `build_manifest`，或至少补齐 §7.1 同名字段。

#### P1-4 gold 三源未强制同源（当前数值碰巧一致）

- **位置**：`src/cnjudbench/tools/gold/{fee,deadline,cases}.json` ↔ 工具实现 ↔ `data/public/tool_search_statute.jsonl` 的 `gold.answer`
- **证据**：实测 fee/deadline 夹具与实现 7+6 条全等；19 题 item gold 与沙箱结果 0 mismatch。但 **`mock_tools_adapter` 直接回放 `gold.calls` + `gold.answer`**（`adapters/mock.py:100-105`），**不把 `sandbox.execute` 的 result 写回 answer**；`test_calc_gold` 只锁 gold JSON ↔ 实现，**无测试锁 item.gold ↔ 工具输出**。
- **影响**：改 `fee.py` 累进表而忘记改题面 gold 时，mock e2e 仍 100.00（假阳性）。
- **修法**：e2e 增加「对每题 `gold.calls` 真跑沙箱，断言 result 与 `gold.answer` 一致」；或 mock:tools 的终答从沙箱 result 合成。

#### P1-5 测试环境假绿 / 假红

- **证据**：仓库外 `D:\APP\Anaconda3` 的系统 Python **无法收集**（`from __future__ import annotations` SyntaxError + `ModuleNotFoundError: cnjudbench`）。正确姿势是 `.venv`（README:41-42 已写，但 `python -m pytest` 裸命令会踩坑）。
- **skip/xfail**：全库 **0** 处 `pytest.mark.skip` / `xfail`（已 grep）。182 collected / 182 passed，无静默跳过。
- **mock 假阳性**：`mock:gold` 按 gold 合成满分答案（设计如此）；判分器区分度主要靠 `MockAdapter` 注入负例（`test_e2e_mock_smoke` / `test_fake_tool` / `test_tool_ast`），覆盖尚可，但见 P1-4。
- **修法**：README/CI 显式绑定 `.venv`；`pyproject` 增加 `requires-python` 已有（>=3.11），可在 pytest 侧加 `python_version` marker 防 3.8 误跑。

#### P1-6 holdout 守卫只匹配路径段 `holdout`

- **位置**：`src/cnjudbench/runner/guards.py:20-22`
- **证据**：大小写不敏感的**整段**匹配；`data/holdout_backup`、`my-holdout-x`、URL 编码名不触发。与 P0-4/P0-5 的路径注入叠加时，守卫可被文件名绕过。
- **修法**：normalize 后对任一 path part 做 `holdout` 子串/白名单根目录策略。

#### P1-7 PowerShell / BOM 读入未用 `utf-8-sig`

- **位置**：全库 `read_text(encoding="utf-8")`（含 `load_items_file`、lawkb、yaml）；`cli.main` 已 `stdout.reconfigure(encoding="utf-8")`（Windows 控制台友好）。
- **证据**：当前仓库 **0** 个 UTF-8 BOM 文件；但 Windows/PowerShell 重定向或 `Out-File` 易产出 BOM。`utf-8` 读 BOM 会在首行 JSON/YAML 留下 `\ufeff`，表现为「JSON 解析失败」或题 id 异常。
- **修法**：数据/题面/lawkb/谓词统一 `encoding="utf-8-sig"`；或加载前 `lstrip('\ufeff')`。CI 在 Windows 上跑一次带 BOM 夹具。

---

### P2（清理 / 文档一致性 / 健壮性）

#### P2-1 `score/norm.article_set` 死分支

- **位置**：`src/cnjudbench/score/norm.py:58-62`（`if n and n not in ("", s): out.add(n) elif n: out.add(n)`）
- 两分支都 `add(n)`；`n not in ("", s)` 无意义。建议删条件只保留 `if n: out.add(n)`，并补 `article_set` 空串/纯标点单测（已有部分覆盖）。

#### P2-2 `state_f1` 用 `__import__("cnjudbench.score.norm"…)` 取 `KEY_ALIASES`

- **位置**：`src/cnjudbench/dialog/state_score.py:47-50`
- 顶层 `from ..score.norm import KEY_ALIASES` 即可；避免运行时字符串导入。

#### P2-3 `harness_sha` 文档与实现不符

- **位置**：`src/cnjudbench/runner/manifest.py:17-26`
- docstring 称「非 git 回退源码树 hash」，实现失败一律 `"unknown"`。要么改注释，要么实现树 hash。

#### P2-4 `evaluate_predicates` 未使用局部变量 `comps`

- **位置**：`src/cnjudbench/predicates/registry.py:63`（`comps = list(ctx.task.components) …` 后未用）
- 死代码，删除或用于 `composite` 真正裁剪。

#### P2-5 CLI / 文档签名一致性（已核对，无缺陷但文档未写返回约定）

| 约定 | 代码 | README / impl 文档 | 结论 |
|---|---|---|---|
| `run --task` / `run-all --tasks` / `run-dialog --task` | `cli.py:73-75,94` | README:53-75 一致 | OK |
| `--model mock:gold\|mock:tools\|mock:dialog\|openai:<m>` | `cli.py:161-175` | README:55,63-75 一致 | OK |
| `load_items_file` → `list[tuple[int, Item]]` | `validate/items.py:18-34` | **未在 README/FRAMEWORK 写明** | 调用方均 `for _lineno, item in …` 正确；建议在 API 注释/文档标明 |
| `evaluate_predicates(ctx, preds)` → `(ftp, ptp, diag)` | `registry.py:59-67` | 未写调用约定 | 测试与 runner 一致；建议进 FRAMEWORK 附录 |

#### P2-6 `run-dialog` 的 score–time AUC 近似过粗

- **位置**：`cli.py:486-491`（两点梯形 `(0,0)→(1, mean state_f1)`）
- 与 FRAMEWORK §5「score–time」语义不符；summary 里 `score_time_auc_str` 勿当真 AUC。建议标 `approx` 或只输出 progress 点列。

#### P2-7 CI 门禁只跑 3 个 L1 任务

- **位置**：`scripts/ci_gate.sh:16-19` / `ci_gate.ps1:19-24`
- 不含 `tool_search_statute` / `gaia_fee_deadline` / `tau_jud_intake`。P2 负例（t-fake-001）仅在 pytest，不在 run-all 门禁。建议 CI 追加 L2 mock:tools 断言。

#### P2-8 适配器缓存默认落盘 `.cache/adapter`

- **位置**：`adapters/openai_compat.py:35`；`.gitignore` 已忽略 `.cache/`
- 缓存 JSON **不含** api_key（`cache.py:51-58` 只写 text/tokens/model）——良好。注意：缓存的是**模型输出**，若开启真 API，题面+输出会进本地缓存；共享机器需清理策略。

---

## 测试缺口清单

| # | 必查项 | 现有覆盖 | 缺口 | 优先级 |
|---|---|---|---|---|
| 1 | score/norm | `test_score_norm.py`：归一化、severity 同义、labels_match、set_f1 松匹配、article_set、find_key 别名 | `text_coverage` 0.55 阈值边界；`flatten_answer` 嵌套冲突；`article_set` 多段顿号 + 空串；`set_f1` severity 同义命中路径的显式断言 | P1 |
| 2 | lawkb 中文条号 | `test_score_norm` / `test_lawkb_resolve`：`第二百六十四条→264`、`253之一`；实测 `resolve_article('刑法','第二百六十四条')→ok cl_264_2011` | 中文条号经 **CiteGuard/evaluate_item 全链路**（非仅 normalize 单元）；`第二百五十三条之一` 在真实 lawkb 的 resolve 金样 | P1 |
| 3 | 假调用负例 t-fake-001 | `test_fake_tool.py:35-39` + `test_e2e_mock_l2_l3.py:30-31`（0.00 + fake_tool） | `mock:tools` 重放该夹具时 **gold.answer 仍可被写进 trajectory** 的泄露面；叙述启发式 `_NARRATIVE_RE` 假阴性（未匹配话术）单测 | P2 |
| 4 | stale / wrong_vintage 归零 | `test_e2e_mock_smoke.py:67-82`（0.00 + stale_statute）；`test_predicates_ftp_ptp.py:142-150`；`test_lawkb_resolve.test_wrong_vintage` | **resolve 状态 `wrong_vintage` → taxonomy/归零** 的映射仅通过 CiteGuard 间接测；`not_effective_on_as_of` 归零无 e2e；cap_50 与 zero 同时触发时的优先级已有 compose 单测但无 stale+cap 组合 | P1 |
| 5 | no_fabrication | `test_predicates_ftp_ptp.py:177-200`（编造 version_id→0 / unknown 不记幻觉）；e2e fabricated_case | 叙述性 version_id 不记编造（`ftp.py:227-232`）无单测；`gen` 降级路径无单测 | P1 |
| 6 | τ dialog state_score | `test_state_f1.py`（4 例）；e2e `run-dialog` 冒烟 | **中文键别名**（`KEY_ALIASES`）经 `state_f1`；`case_card` 嵌套；`extra` 惩罚 precision；列表非对称；与 `run_dialog` 终态集成金样 | P1 |
| 7 | 时间切片 as_of | `test_lawkb_resolve` 四态 + 边界右开；`test_citeguard` missing/bad as_of；`test_manifest` as_of_used 非空 | **claim.as_of 优先于题面** 的 `_as_of_for`（`evaluate.py:166-174`）无单测；非 ISO claim.as_of 回落题面无单测；双 as_of 题 `g-06` 只断言 gold 字符串 | P1 |
| 8 | 工具 6 个确定性 | `test_sandbox_registry` / `test_calc_gold`（fee/deadline 金样 + 复跑一致） | `search_statute` / `search_case` / `lint_document` 无金样 JSON；`get_article` 与 CiteGuard 同源性无「双路径一致」断言 | P1 |
| 9 | gold 同源 | gold JSON ↔ 实现有测 | **item.gold ↔ 工具输出** 无测（P1-4） | P0 |
| 10 | 参数 AST 判分 | `test_tool_ast.py` 错型 1/2→50.00 | 业务错误 vs schema 错误未区分（P0-1）；多余 kwargs；`days=True`（P1-1） | P0 |
| 11 | skip/xfail 掩盖 | 0 skip/xfail；182 全绿 | 系统 Python 收集失败会让人误判「测试坏了」（P1-5） | P1 |
| 12 | 密钥落盘 | reports/ 与根目录扫描 0 命中 | 无「写 manifest 后断言无 env 值」的防回归测试 | P2 |

---

## 摘要表

| ID | 级别 | 标题 | 位置 | 一句话修法 |
|---|---|---|---|---|
| P0-1 | P0 | tool_ast 混淆业务失败与参数非法 | `predicates/tools.py:77-78` | 拆 `schema_ok`，AST 只看 schema |
| P0-2 | P0 | tool_sequence 以 `e.ok` 冒充「已调用」 | `predicates/tools.py:58-61` | 按工具名是否出现在 log 计覆盖 |
| P0-3 | P0 | `doc_type` 路径穿越读任意 JSON | `tools/lint_doc.py:22-23` | stem 白名单 / resolve 困在 SCHEMA_DIR |
| P0-4 | P0 | `item_id` 轨迹路径注入 | `runner/manifest.py:115` | 约束 id 字符集后再拼路径 |
| P0-5 | P0 | `predicates_ref` 可读绝对路径 | `runner/evaluate.py:239` | 仅允许 tasks_root 内相对路径 |
| P1-1 | P1 | `bool` 可当 `int` 过 schema | `tools/sandbox.py:90-94` | bool 对数值类型一律拒绝 |
| P1-2 | P1 | Manifest 缺 user_seed/每题 hash/lock | `runner/manifest.py:39-90` | 按 FRAMEWORK §7.1 补字段 |
| P1-3 | P1 | run-dialog manifest 缺 harness/prompt/lawkb | `cli.py:528-543` | 复用 `build_manifest` |
| P1-4 | P1 | gold 三源无强制同源测试 | `adapters/mock.py:100-105` 等 | e2e 断言沙箱 result ≡ item.gold |
| P1-5 | P1 | 系统 Python 收集失败；裸 `pytest` 假红 | 环境 / README | 文档与 CI 固定 `.venv` |
| P1-6 | P1 | holdout 守卫仅路径整段匹配 | `runner/guards.py:20-22` | 子串/根目录白名单 |
| P1-7 | P1 | 非 `utf-8-sig` 读入遇 BOM 即炸 | 全库 IO | 统一 `utf-8-sig` |
| P2-1 | P2 | `article_set` 死分支 | `score/norm.py:58-62` | 删冗余条件 |
| P2-2 | P2 | `state_f1` 运行时 `__import__` | `dialog/state_score.py:47-50` | 顶层导入 KEY_ALIASES |
| P2-3 | P2 | `harness_sha` 注释不实 | `runner/manifest.py:17-26` | 实现树 hash 或改注释 |
| P2-4 | P2 | `comps` 未使用 | `predicates/registry.py:63` | 删除 |
| P2-5 | P2 | `load_items_file`/`evaluate_predicates` 约定未入文档 | README/FRAMEWORK | 补 API 约定 |
| P2-6 | P2 | score–time AUC 两点近似 | `cli.py:486-491` | 标注 approx 或改真曲线 |
| P2-7 | P2 | CI 不含 L2/L3 门禁 | `scripts/ci_gate.*` | 追加 mock:tools 断言 |
| P2-8 | P2 | 适配器缓存含模型输出 | `adapters/cache.py` | 文档声明缓存敏感度 |

### 合规抽查结论（FRAMEWORK）

| 条款 | 结论 |
|---|---|
| §4.2 工具三谓词语义 | **部分不符**（P0-1/P0-2） |
| §5 工具最小集 6 个 | 符合（`sandbox.py` 注册表） |
| §7.1 Manifest 必填 | **部分不符**（P1-2/P1-3） |
| 密钥不进库/日志/manifest | **符合**（reports 与根 0 密钥；`base.py:3-4` 纪律与实现一致） |
| holdout 隔离 | **部分不符**（P1-6 + 路径注入） |

### 泄露面结论

| 检查项 | 结果 |
|---|---|
| `OPENAI_API_KEY` / `CNJUD_API_KEY` 落盘 | **未发现**（仅 env 读取：`adapters/openai_compat.py:41`；Bearer 头不写文件） |
| reports/manifest 密钥 | **未发现**（抽样 acc-p1p2/ci/dod-final/p2-l2 等；accounting 无密钥字段） |
| 绝对路径（`D:\Claudeworkspace` / `C:\Users\…`） | **reports 与根文档未发现** |
| BOM | **当前 0 文件**；读入路径缺 `utf-8-sig` 防护（P1-7） |

### 测试可跑性结论

- `.venv/Scripts/python -m pytest -q` → **182 passed / 182 collected**，无 skip、无 xfail。
- 系统 Anaconda Python（约 3.8）**收集期 31 errors**（future annotations + 未安装包），属环境误用而非用例缺陷。
- Mock 路径确定性复跑测试存在（`test_dod6_mock_rerun_flip_rate_zero`、`test_e2e_flip_rate_zero_for_p2_tasks`）；gold 同源缺口见 P1-4。

# impl-audit-fix：审计修复执行记录

> 依据 `docs/AUDIT_REPORT.md` + 三份分报告 · 执行日 2026-09-22  
> 回归：`.venv` **197 passed**（含 `tests/test_audit_fixes.py` 新增金样）

## 1. P0 全清

| ID | 修复 | 位置 |
|---|---|---|
| S-P0-1 | statute 双方 `law_id` 非空才比较，禁止 `None==None` 同法 | `predicates/ftp.py` |
| S-P0-2 | claim_extract_miss / 金样不可比 → `skipped=True` 不进 FTP 基数 | `ftp.py` + `base.py` |
| D-P0 | long_horizon canary 改为 `f101–f105`（全库唯一 + 符合 `[0-9a-f]{4,}`） | `data/public/long_horizon_case.jsonl` |
| D-P0 | 校验器全库跨文件 id/canary 去重 | `validate/items.py` |
| T-P0-1 | `ToolLogEntry.schema_ok`；tool_ast 只看 schema；多余 kwargs 按 arg_schema 拒 | `tools/sandbox.py` + `predicates/tools.py` |
| T-P0-2 | tool_sequence 按**工具名出现在日志**计覆盖；业务失败记 `tool_arg_invalid` | `predicates/tools.py` |
| T-P0-3 | `lint_document.doc_type` stem 白名单 + resolve 困在 SCHEMA_DIR | `tools/lint_doc.py` |
| T-P0-4 | 轨迹文件名 `_safe_item_id` 字符白名单 | `runner/manifest.py` |
| T-P0-5 | `predicates_ref` 禁绝对路径/`..`，且 resolve 必须在 task_dir 内 | `runner/evaluate.py` |

## 2. P1（影响分可信 / 合规）已修

- **exact 不放水**：`field match:exact` 只比 accepted/别名；松匹配须显式 `match: labels|contains|severity`
- **中文条号千/万位**：`第一千二百六十条→1260`、`第一千零一条→1001`
- **stale/wrong_vintage 强制 0.00**（compose_score 写死；FRAMEWORK §3.1 与 DoD 对齐为 0.00，废 ×0.50）
- **同法异条 taxonomy**（`wrong_article`）PASS 也进报表
- **Hall −20/处**：`fabricated_case` 题级扣分，下限 0.00
- **state_f1 空 want** 不再记 0；空白元素过滤；顶层 `KEY_ALIASES` 导入
- **gold 无可比要件** → skipped n/a，禁止 0.00 充数
- **非 PredicateError 崩卷** → 单题兜底拒判 n/a
- **fake_tool** 校验 expected∩called（不能被无关成功调用顶替）
- **as_of_used** 记生效 ISO；**utf-8-sig** 读入
- **bool≠int**（amount / tool schema）
- **holdout 守卫** 路径段子串匹配
- **a-007** 金样条号 509→**506**（rule_article / citations / anchors）
- **tau state_goal** 补 `risk_note`（tj-002…005）
- **c-008 旧法** 改挂 `predicates_legacy.yaml`，不再被「禁引合同法」误伤
- **u_element** 全题挂 `rubric_id: u_element_r1`
- **capability** task 与题面对齐：`tool_search_statute=R/U/G`、`gaia=U/O/K`
- **diagnostic_drop(None)** → n/a；**fmt2** 拒绝非有限值

## 3. P2 已顺手清

- `article_set` 死分支、重复 `_WS`、`KEY_ALIASES`「案件类型」双挂、`__import__`、`comps` 死代码
- `harness_sha` 注释改为与实现一致（git / unknown）

## 4. 明确残留（未假装修完）

| 项 | 原因 | 建议 |
|---|---|---|
| lawkb 缺「诉讼费用交纳办法 / 民诉 / 刑诉」 | 需权威条文文本与版本窗，不宜臆造入库 | 下轮补 `scripts/build_min_lawkb` 或改题面 anchors 为库内条 |
| over_refuse 对偶负例、tau 应拒题 | 新题面需合议（status: draft） | 按 FRAMEWORK §1 Abst 双标签补题 |
| tau/long rubric、双 as_of 题 | 同上，数据扩充 | 后续数据轮 |
| Manifest 补 user_seed / 每题 hash / deps lock | 字段扩展牵动 CLI 多处 | 单独小 PR |
| run-dialog 手写 manifest | 同上 | 复用 `build_manifest` |
| gold 三源强制同源 e2e | 需 mock 沙箱重放夹具 | 补测试 |
| CI 门禁未含 L2 | 脚本扩展 | `ci_gate` 追加 mock:tools |

## 5. 验证

```text
.venv/Scripts/python -m pytest -q
→ 197 passed（原 182 + 新 15）
```

回归金样见 `tests/test_audit_fixes.py`（条号千位、skipped 基数、stale 归零、
exact 负例、tool_ast/sequence、路径穿越、fake_tool、None==None 等）。

*未 commit（按纪律等用户指令）；未动会话 cwd 可视化面板文件。*

# P0a 实施文档 — 地基（lawkb + 校验 + 冒烟任务包）

> 对齐 `FRAMEWORK.md` §11 **P0a** 与附录 **C/D**。  
> 范围：工程骨架 + **lawkb 多版本解析** + 题面/谓词 Schema 校验 + **1 个机检任务包跑通**。  
> **不做**：模型调用、FTP/PTP 执行器本体、CiteGuard 三检、Judge（属 P0b/P1）。

---

## 0. 一句话

把「设计里的 lawkb / 题面协议」变成 **可校验、可解析、可冒烟** 的代码地基；给 P0b 留干净接口，不写业务 runner。

## 1. 范围

| 做 | 不做 |
|---|---|
| `pyproject` + 包骨架 + 冒烟测试 | OpenAI / vLLM adapter |
| lawkb schema（YAML）+ 名称归一 + `as_of` 解析 | FTP/PTP 执行器 |
| 题面 JSONL / predicates / task.yaml 校验 | CiteGuard 三检完整逻辑 |
| 1 个任务包 `cit_validity` + 最小条文表 | Judge、工具沙箱、报告层 |
| CLI：`cnjudbench validate` / `cnjudbench resolve-law` | 对外跑分排行榜 |

## 2. 交付物

```text
pyproject.toml
src/cnjudbench/
  __init__.py
  lawkb/
    schema.py       # pydantic / dataclasses 校验模型
    store.py        # 加载 laws/*.yaml + text/
    resolve.py      # normalize + as_of 切片
    cli.py          # resolve-law 子命令（可并入顶层 cli）
  schemas/
    item.py         # 题面（附录 C）
    task.py         # task.yaml / predicates.yaml
  validate/
    items.py
    tasks.py
    matrix.py       # output_type × 谓词适用面（§4.2.1）
  scale.py          # 百分制映射（仅函数 + 单测，P0b 接）
  cli.py            # validate / resolve-law
lawkb/
  laws/*.yaml
  text/*.txt
  VERSION           # store_version，SemVer
tasks/cit_validity/
  task.yaml
  predicates.yaml
  reference.md
  README.md
data/public/cit_validity.jsonl
tests/
  test_lawkb_resolve.py
  test_item_schema.py
  test_predicate_matrix.py
  test_scale.py
  test_smoke_cit_validity.py
```

## 3. 技术选型（锁定）

| 项 | 选择 | 理由 |
|---|---|---|
| 语言 | Python 3.11+ | 评测生态、个人维护 |
| 包管理 | `pyproject.toml` + 可编辑安装 | 可复现 |
| 校验 | `pydantic` v2 | schema 即代码 |
| lawkb 存储 | **YAML 文件树**（非 SQLite） | diff 友好、个人可审；P0 不引入 DB |
| 测试 | `pytest` | 标准 |
| 分数 | `decimal` ROUND_HALF_EVEN → `xx.xx` 字符串 | 与总则一致 |

## 4. lawkb（附录 D 落地）

### 4.1 文件布局

```text
lawkb/
  VERSION                 # 如 lawkb-2026.09.1
  laws/npc_criminal_law.yaml
  laws/npc_civil_code.yaml
  laws/spc_*.yaml         # 司法解释
  text/<version_id>.txt   # 条文正文，一版一文件
```

### 4.2 记录模型（与 D.2 对齐）

- `LawMeta`：`law_id`, `names[]`, `level`, `promulgated_on`, `interprets?`, `abolished_on?`
- `ArticleVersion`：`law_id`, `article_no`, `version_id`, `text_hash`, `effective_from`, `effective_to`, `superseded_by`, `text_ref`, `note`
- 加载时校验：`text_ref` 存在；`text_hash` 与文件内容一致；`effective_to` 开区间；`version_id` 全局唯一。

### 4.3 解析器 API

```python
def normalize_law_name(raw: str) -> ResolveName
    # 去书名号/空白/全半角 → 别名精确命中 → law_id
    # 未命中: status=unresolved（禁止编辑距离归并）

def resolve_article(law: str, article: str, as_of: date) -> ResolveResult
    # D.4：effective_from <= as_of < coalesce(effective_to, ∞)
    # 恰一 → ok | 零 → not_effective_on_as_of / not_yet_effective / wrong_vintage
    # 多一 → ambiguous_versions（报警，拒判）
    # 条号规范化："264条" ≡ "264"；支持 "264之一"
```

`ResolveResult` 必含：`status`, `law_id?`, `article_no_norm?`, `version_id?`, `text?`, `text_hash?`。

未入库条号 → `unknown_in_lawkb`（**不是**幻觉）。

### 4.4 切片 hash（manifest 预留）

```python
slice_union_hash = sha256(concat(sorted(text_hash of resolved version_ids)))
```

P0a 只实现纯函数 + 单测；写入 manifest 留给 P0b。

### 4.5 P0 最小条文表（D.6）

| 内容 | 数量 | 用途 |
|---|---|---|
| 刑法 · 分则常用条 | ≥ 8 版本（含修正时点） | `cit_validity` + 时效 |
| 民法典 · 合同/总则常用条 | ≥ 4 版本 | 别名与多版本 |
| 司法解释 | 2–3 条 | `level` 与 `interprets` |

条文正文可用**公开法律文本节录**（注意许可，见 FRAMEWORK §10）；测试夹具允许 `text` 为短夹具句，但 `text_hash` 必须真实。

## 5. 题面 / 任务包 Schema

### 5.1 Item（附录 C 子集强制）

必填：`id, task_id, capability, difficulty, interaction, roles[], domain, output_type, hcut[], instruction, input, gold, law_anchors[], as_of, canary, split, contamination_risk, source`  
条件：`output_type == "composite"` ⇒ `components[]` 非空且 ∈ 单型枚举。  
枚举与 FRAMEWORK §4.2.0 / 附录 C **逐字一致**（`output_type` 10 值；`hcut` 5 值；`interaction` 5 值）。

### 5.2 任务包三件套

- `task.yaml`：标签、prompt 模板、oracle、interaction
- `predicates.yaml`：`ftp[] / ptp[] / diagnostic_ftp[]?`，字段 `type, …, as_of?, on_fail`
- `reference.md`：参考解（**不得**进 prompt）
- `README.md`：意图、许可、污染、`Verified` 状态（P0 可为 `draft`）

### 5.3 适用面矩阵（§4.2.1，P0 必须实现校验）

`validate/matrix.py` 用显式表：`allowed[(predicate_type, output_type)] -> bool`。  
校验失败 = 任务包 **不得** 进 `active`。新建谓词类型必须同步改表（注释写明）。

## 6. 冒烟任务包：`cit_validity`

选型理由：横切能力、`output_type: structured`、机检路径短、直接吃 lawkb 解析（存在/条号/时效）。

| 项 | 值 |
|---|---|
| capability | 横切 `Cit`（可标 `hcut: ["Cit","Hall"]`） |
| interaction | `L1` |
| output_type | `structured` |
| gold | `[{law, article, as_of, expect_status}]` |
| FTP | `statute` 命中声明锚点；`no_fabrication`（结构化字段） |
| PTP | `must_not_statute`（禁引列表内法条） |
| 题量 | public **8–12** 条：有效 / 未生效 / 已失效 / 未入库 / 错条号 各覆盖 |
| as_of | 至少 2 个不同日期，验证切片 |

机检（P0a 边界）：**只跑 lawkb 解析器** 与 schema 校验，产出「期望 status vs resolve status」对照表；**不**调用模型。  
模型侧执行器 = P0b。

## 7. 百分制（仅 scale 函数）

`metrics/scale.py`（或 `scale.py`）实现总则映射：

- `to_percent_unit(x) = 100 * x`（x∈[0,1]）
- `to_percent_rubric(v, lo, hi)` 分段
- `gate_zero` / `cap_50` 辅助
- `fmt2(x) -> "xx.xx"`（ROUND_HALF_EVEN）

P0a 只锁单测；不做聚合报表。

## 8. CLI（P0a）

```bash
python -m cnjudbench validate --items data/public --tasks tasks
python -m cnjudbench resolve-law --law 刑法 --article 264 --as-of 2024-06-01
python -m cnjudbench smoke-cit-validity   # 解析器 vs gold status 对照，exit 0/1
```

退出码：校验失败 / smoke 不一致 → 非 0。

## 9. 测试与 DoD

| 测试 | 断言 |
|---|---|
| `test_lawkb_resolve` | D.4 四态；条号规范化；ambiguous 报警；`unknown_in_lawkb` |
| `test_item_schema` | 枚举闭合；composite 必填 components；split×contamination 规则 |
| `test_predicate_matrix` | gen 无 field_keep PTP 等适用面拒绝 |
| `test_scale` | 两位小数、half-even、gate/cap |
| `test_smoke_cit_validity` | 全部金样 status 与 resolve 一致 |

**P0a DoD**：

1. `pytest` 全绿。  
2. `validate` 对 `tasks/cit_validity` + public 题面通过。  
3. `smoke-cit-validity` 覆盖至少 5 种 resolve status。  
4. `slice_union_hash` 单测稳定（同输入同 hash）。  
5. README 目录树与真实一致；holdout 仍被 ignore。

## 10. 实施顺序（小步）

| 步 | 内容 | 验证 |
|---|---|---|
| 1 | `pyproject` + 空包 + 一条 pytest | 绿 |
| 2 | lawkb schema + store 加载/hash | 单测 |
| 3 | normalize + resolve（D.3/D.4） | 单测四态 |
| 4 | 最小条文表 + 文本 | hash 一致 |
| 5 | Item/Task/Predicates schema + matrix | 非法样例拒收 |
| 6 | `cit_validity` 任务包 + 8–12 题 | validate 过 |
| 7 | `smoke-cit-validity` + scale 单测 | DoD |

## 11. 风险与边界

- **条文文本许可**：公开法条节录入 `lawkb/text/`；库 SemVer 与数据许可分表（FRAMEWORK §10）。  
- **禁止**模糊法名匹配（防《刑法》↔《刑法修正案》）。  
- **禁止**用 `store_version` 发行日冒充 `as_of`。  
- P0a **不**产出模型分数；smoke 只证明解析与题面协议可执行。  
- 不构成法律意见（声明见 FRAMEWORK §12.1）。

## 12. 与 P0b 的接口

P0b 直接使用：

- `resolve_article` / `slice_union_hash`
- Item 加载后的 `law_anchors` + `as_of`
- `validate.matrix` 的谓词适用面
- `scale.fmt2`

P0b 新增：FTP/PTP 执行器、CiteGuard 三检、API adapter、manifest 写入。

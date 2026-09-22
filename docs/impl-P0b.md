# P0b 实施文档 — 双谓词 + CiteGuard + API/Manifest

> 对齐 `FRAMEWORK.md` §11 **P0b**、§4.2–4.3、§7.1、附录 B。  
> 前置：`docs/impl-P0a.md` §12 接口已落地（`resolve_article` / `slice_union_hash` / `validate.matrix` / `scale`）。  
> **目标**：模型输出 → 机检判分 → Run Manifest，跑通 3 个 L1 冒烟包。  
> **不做**：Judge/rubric 主观分、工具沙箱、τ-Jud、holdout 门禁（P1）。

---

## 0. 一句话

在 P0a 地基上接好「双谓词 oracle + CiteGuard + OpenAI-compat 适配 + manifest」，使 `cit_validity` / `extract` / `structured` 三类 L1 题可离线机检出分（百分制两位小数）。

## 1. 范围

| 做 | 不做 |
|---|---|
| FTP/PTP 执行器（尊重 §4.2 适用面） | 自由文本语义 PTP |
| CiteGuard 三检（存在/条号/时效） | Min-K% / canary 污染双检 |
| OpenAI-compat adapter + 缓存 + token 账本 | 多模态 / 复杂流式 |
| Run Manifest（§7.1 必填项） | 对外榜单与 CI 门禁 |
| 再 2 个 L1 冒烟包（extract / structured） | tool_call / composite 整链路 |
| 失败 taxonomy 标签落盘 | Judge 成本核算 |

## 2. 交付物

```text
src/cnjudbench/
  predicates/
    base.py         # PredicateResult, on_fail 动作
    ftp.py          # statute | element | field | amount | deadline | …
    ptp.py          # must_not_statute | field_keep | state | …
    registry.py     # type → 实现；与 validate.matrix 对齐
  citeguard/
    extract.py      # claim 抽取（structured 优先；gen 仅声明段）
    check.py        # 三检 → CiteCheckResult
  adapters/
    base.py         # ModelAdapter 协议
    openai_compat.py
    mock.py         # 离线金样/固定响应（测试用）
  runner/
    evaluate.py     # 单题：prompt → response → predicates → score
    manifest.py     # RunManifest 写盘
    account.py      # token/$/latency 账本
tasks/
  u_element_extract/     # extract 冒烟包
  s_charge_subsume/      # structured 冒烟包（8–12 题）
data/public/…
tests/
  test_predicates_ftp_ptp.py
  test_citeguard.py
  test_adapter_mock.py
  test_manifest.py
  test_e2e_mock_smoke.py
```

## 3. 谓词执行器（§4.2 / 附录 B）

### 3.1 结果模型与合成顺序

```text
PredicateResult =
  { type, target?, passed: bool, on_fail, detail,
    failure_taxonomy?: §5.2 标签 }

题分合成顺序（强制，写死在 evaluate.py）：
  1) 各 FTP 得分（命中比例 / exact）
  2) 各 PTP 调整（field_keep 失败 → cap_50 或 partial）
  3) gate：on_fail=zero 的 FTP 失败 → 整题 0.00
  4) scale.fmt2 输出 xx.xx
```

**on_fail 动作**（附录 B）：

| 值 | 行为 |
|---|---|
| `zero` | 该题 score = 0.00（一票否决） |
| `cap_50` | score = `scale.cap_at(score, 50.00)` |
| `partial` | 按命中字段 F1 比例计 |
| `flag` | 不改分，仅记 taxonomy / 报告 |

### 3.2 P0b 必实现谓词

| type | 判定要点 | 典型 on_fail |
|---|---|---|
| `statute` | 输出引用 ⊇ FTP 必引（经 CiteGuard 解析后比 law_id + article_no_norm） | zero |
| `must_not_statute` | 输出引用 ∩ 禁引表 = ∅ | cap_50 |
| `element` / `field` | gold 字段命中（别名表可配） | partial |
| `field_keep` | 预测结构化字段不被改坏（如 as_of） | cap_50 |
| `amount` / `deadline` | 数值/日期精确或容差（默认 0） | partial |
| `no_fabrication` | 引用均能 resolve；version_id 非编造 | zero |
| `schema` / `lint` | 仅 structured/extract 栏目级；gen 不做自由文本 PTP | flag |

**禁止**：对 `gen` 原文做字符串 diff 式 PTP；gen 的 statute 检查 **只走 claim 抽取**（§4.2 脚注）。

### 3.3 适用面

执行前调用 `cnjudbench.validate.matrix.predicate_allowed` / `ptp_allowed`；不适用 → **拒判并报错**，不静默跳过。

## 4. CiteGuard 三检（戒律 4 / 附录 D）

### 4.1 claim 抽取（extract.py）

| 输出型 | 策略 |
|---|---|
| `structured` | 读 `citations[]` / `law_anchors` 字段（schema 校验） |
| `choice` / `exact` / `short` | 选项或金样锚点；预测侧若带引用列表则检 |
| `gen` | **仅**任务包声明的 JSON 段或引用列表；抽不到 → 降级 `claim_extract_miss` 标记，**不得**正则扫全文 |

Claim 形状：`{law_raw, article_raw, as_of, quote?}` → `resolve_article(law, article, as_of, store)`。

### 4.2 三检（check.py）

| 检 | 失败条件 | failure_taxonomy |
|---|---|---|
| 存在 | `unresolved_law` / `unknown_in_lawkb` | `wrong_article`（unknown **分列**，不记幻觉） |
| 条号 | normalize 后与 gold/必引不一致 | `wrong_article` |
| 时效 | `wrong_vintage` / `not_yet_effective` / `not_effective_on_as_of` | `stale_statute` |

`ok` 且与 FTP 对齐 → 通过。`ambiguous_versions` → 拒判 + 系统报警（库数据错误）。

### 4.3 与判分耦合

- FTP `statute` 失败 → `on_fail: zero`，标签 `miss_retrieve` 或 `wrong_article`。
- 编造 version_id / 不存在条文仍言之凿凿 → `no_fabrication` + `fabricated_case`。
- 时效错误 → `stale_statute`。

## 5. API Adapter（§7）

### 5.1 协议（adapters/base.py）

```python
class ModelAdapter(Protocol):
    model_id: str          # 如 "openai:gpt-4o"
    revision: str | None   # 写入 manifest
    def complete(self, prompt: str, *, temperature: float = 0.0,
                 seed: int | None = None) -> CompletionResult

CompletionResult = { text, usage: {prompt_tokens, completion_tokens},
                     latency_ms, raw? }
```

### 5.2 OpenAI-compat（openai_compat.py）

- `base_url` + `/chat/completions`；支持本地 vLLM / 任意 compat 端点。
- 鉴权：环境变量 `OPENAI_API_KEY` / `CNJUD_API_KEY`（**不进库、不进日志**）。
- 采样默认 `temperature=0`；`seed` 可选，写入 manifest。
- 超时记 `timeout`；网络错误重试 ≤2（禁止改温度重试刷分）。
- 缓存键：`sha256(model_id|revision|prompt|temperature|seed)`；换 revision 必须 miss。

### 5.3 MockAdapter（mock.py）

- 读题面 `gold` 或夹具响应文件；**零网络**，供 CI/冒烟。
- e2e 冒烟 **必须** 可用 Mock 全绿，不依赖真 API。

## 6. Run Manifest（§7.1，缺一不发）

```yaml
run_id: "…"
created_at: "…"
harness_sha: "…"                 # git SHA 或源码树 hash
lawkb:
  store_version: "lawkb-…"       # lawkb/VERSION
  as_of_used: ["2024-06-01", …]  # 本 run 实际触达
  slice_union_hash: "sha256:…"   # resolve.slice_union_hash
model:
  model_id: "openai:gpt-4o"
  revision: "…"
  temperature: 0.0
  seed: 42
prompt_hash: "sha256:…"
dataset:
  task_ids: ["cit_validity", "u_element_extract", "s_charge_subsume"]
  item_count: N
  item_content_hash: "sha256:…"
accounting:
  prompt_tokens: …
  completion_tokens: …
  est_cost_usd: …                # 可 null（本地）
  judge_calls: 0                 # P0b 恒 0
  p95_latency_ms: …
disclaimer: "本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。"
```

写入：`reports/runs/<run_id>/manifest.json`（目录已 gitignore）。

## 7. 冒烟任务包（P0b 增量）

| task_id | output_type | 题量 | 机检点 |
|---|---|---|---|
| `cit_validity`（已有） | structured | 12 | CiteGuard 三检 + no_fabrication |
| `u_element_extract` | extract | 8–12 | FTP field/element + PTP field_keep |
| `s_charge_subsume` | structured | 8–12 | FTP element + statute；PTP must_not_statute |

约束：四件套齐全；`output_type` 闭合枚举；适用面矩阵通过；法条锚点全称 + `as_of`；extract/structured **禁止**自由文本 PTP。

## 8. CLI

```bash
python -m cnjudbench run --task cit_validity --model openai:gpt-4o --base-url … --out reports/runs/<id>
python -m cnjudbench run --task u_element_extract --model mock:gold --out reports/runs/smoke-extract
python -m cnjudbench run-all --tasks cit_validity,u_element_extract,s_charge_subsume --model mock:gold
```

stdout：各题 `xx.xx` + task 均分（排序用未舍入值，展示 `fmt2`）+ `slice_union_hash` + disclaimer 一行。

## 9. 测试与 DoD

| 测试 | 断言 |
|---|---|
| `test_predicates_ftp_ptp` | 各谓词正/负例；on_fail 四态；合成顺序（zero 优先于 cap） |
| `test_citeguard` | 三检；unknown ≠ hallucinated；ambiguous 拒判 |
| `test_adapter_mock` | Mock 确定性；temperature=0 同 prompt 同输出 |
| `test_manifest` | §7.1 必填项齐全；slice_union_hash 与 P0a 向量一致 |
| `test_e2e_mock_smoke` | 3 任务包 Mock 跑通；分数 `0.00`–`100.00` 两位小数 |

**P0b DoD**：

1. `pytest` 全绿（含 P0a 60 项回归）。
2. Mock 下 3 任务包 `run-all` 产出 manifest + summary.json。
3. 人为 `wrong_vintage` / 幻觉引用样例 → 0.00 或 cap，taxonomy 正确。
4. `field_keep` 篡改 as_of → cap_50。
5. 真 API 跑通 1 次冒烟（可选记录）；CI 仅 Mock。
6. 复跑 Mock：谓词级翻转率 0（确定性）。

## 10. 实施顺序

| 步 | 内容 | 验证 |
|---|---|---|
| 1 | predicates base + on_fail + registry | 单测 |
| 2 | CiteGuard extract + 三检 | 单测 |
| 3 | FTP/PTP 全量实现 | 单测 |
| 4 | MockAdapter + OpenAI-compat | 单测 + 手动 1 次真调 |
| 5 | runner + manifest + account | 单测 |
| 6 | `u_element_extract` 任务包 | validate |
| 7 | `s_charge_subsume` 任务包 | validate |
| 8 | CLI run/run-all + e2e mock | DoD |

## 11. 风险与边界

- **gen 抽取失败**：抽不到 claim 时 **不得** 降级为全文正则；报告标 `claim_extract_miss`。
- **adapter 密钥**：仅环境变量；日志脱敏。
- **缓存污染**：换 model revision 必须换缓存键。
- **翻转率**：Mock 必须 0；闭源 API 温度 0 仍可能抖，超限写 `limits.md`。
- P0b **不含** Judge；`judge_calls` 恒 0，避免成本幻觉。
- 法条「待校对」条目不阻塞 Mock 冒烟，正式对外分前须核（承接 P0a 风险）。

## 12. 与 P1 的接口

- `PredicateResult` / `CiteCheckResult` → 红线与失败 taxonomy 报告。
- `RunManifest` 已预留 `judge_calls` / `est_cost_usd`。
- `on_fail` 枚举与 `scale.gate_zero` / `cap_at` 可被 rubric gate 复用。
- 任务包 `rubric.yaml` 字段位保持，P1 再填。

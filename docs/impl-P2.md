# P2 实施文档 — 工具沙箱 / Legal-Tool-Bench / Legal-GAIA

> 对齐 `FRAMEWORK.md` §2、§5、§11 **P2**。  
> 前置：P0a/P0b 机检链路 + P1（含收尾）Judge/红线可用。  
> **目标**：L2 工具调用可判分 + L3a 精品多步轨迹，假调用可检测。  
> **不做**：τ-Jud / 整案长程（P3）。

---

## 0. 一句话

让模型「真的会调工具、调对工具」，并在卷宗包多步任务上出 exact 终答分与 progress——假调用、漏调、参数错都要扣到分上。

## 1. 范围

| 做 | 不做 |
|---|---|
| 6 工具沙箱（本地确定性实现） | 真实外网检索 |
| Legal-Tool-Bench（L2，`tool_call`） | 任意第三方工具 |
| Legal-GAIA 精品 10 题（L3a，`exact`） | 大规模 GAIA 全集 |
| AST/参数校验 + 假调用检测 | 工具「评语」语义分 |
| progress rate + 步数成本 | 用户模拟对话 |
| Manifest 记 tool 轨迹 hash | |

## 2. 工具最小集（沙箱）

| 工具 | 输入 | 输出（确定性） | 判分点 |
|---|---|---|---|
| `search_statute` | query, as_of | lawkb 命中列表 | 该调未调 / 参数 |
| `get_article` | law, article, as_of | 条文文本或 unknown | as_of 正确 |
| `search_case` | facts keywords | 夹具案例 id 列表 | 假调用 |
| `calc_deadline` | start, days/type | ISO 日期（金样） | exact |
| `calc_fee` | amount, type | 诉讼费（金样表） | exact |
| `lint_document` | doc_type, fields | 栏目错误列表 | schema |

**目录**：

```text
src/cnjudbench/tools/
  sandbox.py       # 注册表、调用日志、禁外网
  statutes.py cases.py deadline.py fee.py lint_doc.py
  gold/            # calc 金样
tools/schema/*.json
tasks/tool_search_statute/
tasks/gaia_fee_deadline/
data/public/…
```

## 3. Legal-Tool-Bench（L2）

- `output_type: tool_call`；交互 L2。  
- 轨迹：`[{name, args_ast, result_ref}]`；判分：  
  - **该调**：FTP `progress_keyword` 弱 + 期望工具序列（子集匹配）  
  - **参数 AST**：`schema`/`lint`（§4.2 矩阵 tool_call 列）  
  - **假调用**：声称调用但 sandbox 无日志 → `fake_tool`，`on_fail: zero`  
  - **副作用** `state`：若声明（P2 末）  
- 题量：每工具 ≥3 题，合计 **18–24**。

## 4. Legal-GAIA（L3a 精品 10）

- 卷宗包：`packets/<id>/`（起诉状节录、证据清单、时间线 JSON）。  
- 期望：多步（检索 → 计算 → 终答）；`output_type: exact`。  
- 指标：`resolve rate ×100` + hidden-answer（gold 不进 prompt）+ progress（关键步关键词）。  
- 题面 **10** 题精品：诉讼费、期间、条号、金额混合；双 `as_of`。

## 5. 假调用与沙箱纪律

1. 仅允许注册表内 6 工具；未知名 → `fake_tool`。  
2. 未执行只叙述「我搜索了…」→ 无 log → `fake_tool`。  
3. 沙箱 **禁外网、禁子进程**；时间/随机须可注入种子。  
4. 轨迹写入 `items/<id>.trajectory.json`，hash 进 manifest。

## 6. 评分（接 P0b/P1）

```text
L2 题分 = 工具序列匹配分 × 参数正确分 − fake_tool 零分
L3a 题分 = exact(0/100) 主分；progress 诊断列；步数进 cost
均经 scale.fmt2；gate 规则沿用（zero 优先）
```

## 7. CLI

```bash
python -m cnjudbench run --task tool_search_statute --model mock:tools --out reports/runs/t1
python -m cnjudbench run --task gaia_fee_deadline --model mock:gold --out reports/runs/g1
python -m cnjudbench validate --items data/public --tasks tasks   # 含 L2/L3a 包
```

## 8. 测试与 DoD

| 测试 | 断言 |
|---|---|
| `test_sandbox_registry` | 6 工具可调；外网/未知名拒绝 |
| `test_calc_gold` | deadline/fee 金样逐条 |
| `test_fake_tool` | 无日志声称调用 → 0.00 + `fake_tool` |
| `test_tool_ast` | 参数 schema 拒绝错误 AST |
| `test_gaia_exact` | 精品题 gold exact；progress 单独可算 |
| `test_e2e_mock_l2_l3` | Mock 全流程 exit 0，分数两位小数 |

**P2 DoD**：

1. 全量 pytest 绿（含 P0/P1 回归）。  
2. L2 + L3a 任务包过 validate + 适用面。  
3. 假调用夹具必现 0.00。  
4. Mock 下 L2/L3a run 产出 summary/manifest（轨迹 hash）。  
5. `calc_*` 金样测试锁定。  
6. 真模型可选冒烟，不阻塞。

## 9. 顺序

| 步 | 内容 | 验证 |
|---|---|---|
| 1 | sandbox + 6 工具 + 金样 | 单测 |
| 2 | 轨迹日志 + fake_tool | 单测 |
| 3 | tool_call 谓词（序列/AST） | 单测 |
| 4 | `tool_search_statute` 任务包 | validate |
| 5 | `gaia_fee_deadline` 10 题 | validate |
| 6 | CLI + e2e mock | DoD |
| 7 | manifest 轨迹 hash | 单测 |

## 10. 风险与边界

- **禁止** 用 L1 分冒充可部署（交互层标签强制）。  
- 工具结果夹具需与 lawkb `as_of` 一致，防金样与库打架。  
- 精品 10 题少而全，**不**为题量放水。  
- `search_case` 仅夹具，不接外网案例库；许可与题面伦理仍见 FRAMEWORK §10/§12。

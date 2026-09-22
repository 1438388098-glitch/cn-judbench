# CN-JudBench（法衡）

中国司法多维度大模型 / 司法 Agent 评测框架（设计文档 + 待落地 P0）。

**目标**：测出模型在中国司法工作流里「哪一维能用、哪一维危险、是否稳定、代价多少」。  
**分数**：百分制，保留两位小数（0.00–100.00）。  
**非法律意见**：评测结果不得用于司法裁判、合规放行或当事人决策。

## 文档

| 文件 | 说明 |
|---|---|
| [FRAMEWORK.md](FRAMEWORK.md) | 框架设计定稿 **v0.3.1**（能力维、谓词、lawkb、指标、防作弊） |
| [index.html](index.html) | 设计文档可读版（浏览器预览） |
| [docs/research-notes.md](docs/research-notes.md) | 第一轮调研：中文法律评测 |
| [docs/research-notes-round2.md](docs/research-notes-round2.md) | 第二轮调研：coding / agent / 工程硬化 |
| [docs/impl-P0a.md](docs/impl-P0a.md) | **P0a 实施文档**（lawkb + 校验 + 冒烟任务包） |

## 项目状态

- [x] 设计与调研（v0.3.1，含外部审查修订）
- [x] **P0a 实施文档**（`docs/impl-P0a.md`）
- [ ] **P0a 代码** lawkb schema + 校验 + 1 个冒烟任务包
- [ ] **P0b** FTP/PTP 执行器 + CiteGuard + API adapter
- [ ] P1 Judge / 红线 / CI 门禁
- [ ] P2 工具层 / Legal-GAIA

## 如何跑评测（P0 落地后）

```bash
# 示意：以实际 CLI 为准
python -m cnjudbench.run --task cit_validity --model openai:gpt-4o --as-of 2024-06-01
# 产出 reports/runs/<run_id>/summary.json（百分制两位小数）+ manifest.json
```

当前仅有设计文档，**尚无可执行 runner**。

## 如何加题

1. 在 `tasks/<task_id>/` 建任务三件套：`task.yaml` + `predicates.yaml` + `reference.md`（主观另加 `rubric.yaml`）。  
2. 题面放 `data/public|holdout|live/*.jsonl`，字段见 FRAMEWORK 附录 C。  
3. 谓词必须符合 §4.2 的 **output_type 闭合枚举与适用面**；`composite` 必填 `components`；`hcut` 只能是 `Cit/Abst/Hall/Cons/Proto`。  
4. 法条锚点写全称 + `as_of`，依赖 lawkb 多版本解析（附录 D）。  
5. 通过 schema 校验与 Verified 状态机后再进 `active`。

## 目录规划（P0 起）

```text
lawkb/          # 法条时间轴多版本
tasks/          # 任务包
data/           # public / holdout / live
adapters/ runner/ metrics/ judge/ reports/
docs/           # 调研与校准集
```

## 许可

- 代码：待定（建议 MIT）。  
- **数据 / 题面 / lawkb 文本与代码分表声明**；引用外部数据集前先核对其 LICENSE（见 FRAMEWORK §10）。

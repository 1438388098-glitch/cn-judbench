# CN-JudBench（法衡）

中国司法多维度大模型 / 司法 Agent 评测框架（P0a 地基已落地）。

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
| [docs/impl-P0b.md](docs/impl-P0b.md) | **P0b 实施文档**（FTP/PTP + CiteGuard + API/Manifest） |

## 项目状态

- [x] 设计与调研（v0.3.1，含外部审查修订）
- [x] **P0a 实施文档**（`docs/impl-P0a.md`）
- [x] **P0a 代码** lawkb 多版本解析 + 题面/谓词校验 + `cit_validity` 冒烟（60 项测试）
- [x] **P0b 实施文档**（`docs/impl-P0b.md`）
- [ ] **P0b 代码** FTP/PTP 执行器 + CiteGuard + API adapter
- [ ] P1 Judge / 红线 / CI 门禁
- [ ] P2 工具层 / Legal-GAIA

## 如何跑（P0a 现状）

```bash
# 环境：Python 3.11+，装依赖与包
py -3.13 -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"

# 校验任务包与题面（schema + §4.2.1 适用面矩阵 + lawkb 完整性）
python -m cnjudbench validate --items data/public --tasks tasks

# 按 as_of 解析法条版本（附录 D.4：四态 + 条文文本）
python -m cnjudbench resolve-law --law 刑法 --article 264 --as-of 2024-06-01

# cit_validity 冒烟：金样期望 vs 解析器对照（不调用模型）
python -m cnjudbench smoke-cit-validity
```

模型侧 runner（`--model ...` → `reports/runs/<run_id>/summary.json` + manifest）
属 **P0b**，尚未实现。

## 测试

```bash
.venv/Scripts/python -m pytest -q
```

## 如何加题

1. 在 `tasks/<task_id>/` 建任务三件套：`task.yaml` + `predicates.yaml` + `reference.md`（主观另加 `rubric.yaml`）。  
2. 题面放 `data/public|holdout|live/*.jsonl`，字段见 FRAMEWORK 附录 C。  
3. 谓词必须符合 §4.2 的 **output_type 闭合枚举与适用面**；`composite` 必填 `components`；`hcut` 只能是 `Cit/Abst/Hall/Cons/Proto`。  
4. 法条锚点写全称 + `as_of`，依赖 lawkb 多版本解析（附录 D）。  
5. 通过 schema 校验与 Verified 状态机后再进 `active`。

## 目录

```text
src/cnjudbench/  # 包：lawkb 解析 / schemas / validate / scale / smoke / cli
lawkb/           # 法条时间轴多版本（生成脚本 scripts/build_min_lawkb.py）
tasks/           # 任务包（现含 cit_validity）
data/            # public / holdout（ignore） / live
tests/           # pytest
docs/            # 调研、实施文档与校准集
adapters/ runner/ judge/ reports/   # P0b / P1 规划中
```

## 许可

- 代码：待定（建议 MIT）。  
- **数据 / 题面 / lawkb 文本与代码分表声明**；引用外部数据集前先核对其 LICENSE（见 FRAMEWORK §10）。

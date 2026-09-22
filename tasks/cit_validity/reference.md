# cit_validity · 参考解与金样构造规则

## 金样结构

每题 `gold` 为数组，元素四元组：

```json
{"law": "刑法", "article": "264", "as_of": "2024-06-01", "expect_status": "ok"}
```

`expect_status` 与 `cnjudbench resolve-article` 的 `ResolveResult.status` 一一对应：

| status | 语义 |
|---|---|
| `ok` | 恰有一个版本满足 `effective_from <= as_of < effective_to` |
| `wrong_vintage` | 条文存在，但所有版本在 as_of 前已失效（如已废止司法解释） |
| `not_yet_effective` | 条文存在，但最早版本晚于 as_of 生效 |
| `not_effective_on_as_of` | 条文存在、窗口覆盖异常（数据间隙） |
| `unknown_in_lawkb` | 条号未入库（**不是幻觉**，报告与编造分列） |
| `unresolved_law` | 法名别名未命中（框架不擅自猜简称） |
| `ambiguous_versions` | 库数据错误（多版本同窗），拒判报警；不出现在金样 |

## P0a 边界

冒烟只做「gold 期望 vs 解析器实际」对照，**不调用模型**；模型侧执行器属 P0b。

## 构造纪律

1. 覆盖至少 5 种 status；`as_of` 至少 2 个不同日期（验证切片）。
2. `unknown_in_lawkb` 题须选用真实存在但未入库的条号（如刑法第 400 条）。
3. 禁引列表（PTP `must_not_statute`）选用已废止且易误用的文本。
4. 改金标 = lawkb/数据 major 版本（FRAMEWORK §9.2），旧分不并表。

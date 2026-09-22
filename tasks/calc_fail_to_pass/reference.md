# calc_fail_to_pass · 参考解与隐藏用例构造规则

## 计算规则（诉讼费族，cf-001..012）

《诉讼费用交纳办法》第十三条财产案件受理费分段累计：

- ≤10000 元 → 50 元；
- 10000 元以上分段累进：10 万以内 2.5%、10-20 万 2%、20-50 万 1.5%、50-100 万 1%、
  100-200 万 0.9%、200-500 万 0.8%、500-1000 万 0.7%、1000-2000 万 0.6%、2000 万以上 0.5%；
- 不足 1 元四舍五入（`int(total + 0.5)`），最低 50 元。

`formula_id = "fee_tiered_2007"`（2007-04-01 施行版）。

## 隐藏用例契约

`tasks/calc_fail_to_pass/tests/calc/<item_id>.py` 必须定义：

```python
def check(answer: dict) -> tuple[int, int]  # (passed, total)
```

- 期望值在**生成期**由独立脚本按上述规则计算后硬编码（判分路径不读 gold，防金样泄漏）；
- 容差：相对误差 ≤0.5% 或绝对误差 ≤1 元（`_close`）；
- `work.formula_id` 核对规则标识，防止数值碰巧命中而规则错误。
- **规范标识（题面 prompt_template 必须枚举告知，v0.4.1 教训）**：
  `fee_tiered_2007` / `simple_interest_365` / `period_days`。
  初版未在题面告知规范标识，GLM 数值全对却 11/12 因自由文本标识被记半分——
  属 oracle 公平性缺陷而非模型缺陷，已修复并复测（见 docs/calc-hidden-test-report.md）。

## 一致性金样锁

`gold` 与隐藏用例必须同真：`tests/test_calc_task.py` 对每题断言
`check(gold) == (total, total)`——两套真相源漂移即测试失败。

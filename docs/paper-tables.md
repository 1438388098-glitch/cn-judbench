# 论文主表（生成自 runs，正式对比表只收 provisional=false）

> 全部 run 总分历史见 [run-score-ledger.md](run-score-ledger.md)（唯一汇总账）。
> 数据截至：2026-09-24；v0.6 现行基线为 random 7.96 /
> rules 27.40 / mock:gold 100×8 包（reports/runs/baseline-v06c 现行；历史链：
> v06 27.03 → 判分效度修复重导零漂移 baseline-v06b → c417 判分语义修订重导 v06c，
> 演进见 run-score-ledger.md）。**DS-flash v0.6 全 12 包已跑**
> （grand 68.72/hard 76.31/flip 0%/$0.56，ds-flash-v06-full+tools，见
> run-params-ds-flash-v06.md）；GLM v0.6 能力 8 包三档已入账（思考高 69.59 / 思考低 64.18 /
> 思考默认继承 59.14，glm53f-hi/low/iso-scored，2026-09-25 c419 重评）；工具轨 v0.6 重跑待做。
> 引用本表数字前先核对 `生成自 runs` 的时效。

## T-main（正式对比表）

（暂无——缺 deps 锁或 flip 复跑的 run 均为 provisional，见附录）


## T-provisional（附录；provisional=true 不得进 T-main）

| 模型 | rev | cap±CI | hard±CI | safety | solve% | $/solve | pass_k | flip% | baselines | provisional |
|---|---|---|---|---|---|---|---|---|---|---|
| mock:tools | 5e0406e88484 | 80.00 | 80.00 [40.00,100.00] | n/a | 75.00 | n/a | n/a | n/a | random=n/a / rules=n/a | True |

# 论文主表（生成自 runs，正式对比表只收 provisional=false）

> 数据截至：2026-09-23（v0.4.1 期 run）；v0.6 现行基线为 random 7.96 /
> rules 27.03 / mock:gold 100×8 包（reports/runs/baseline-v06），真实模型 v0.6
> 全量复跑因密钥/余额阻塞未做。引用本表数字前先核对 `生成自 runs` 的时效。

## T-main（正式对比表）

（暂无——缺 deps 锁或 flip 复跑的 run 均为 provisional，见附录）


## T-provisional（附录；provisional=true 不得进 T-main）

| 模型 | rev | cap±CI | hard±CI | safety | solve% | $/solve | pass_k | flip% | baselines | provisional |
|---|---|---|---|---|---|---|---|---|---|---|
| mock:tools | 5e0406e88484 | 80.00 | 80.00 [40.00,100.00] | n/a | 75.00 | n/a | n/a | n/a | random=n/a / rules=n/a | True |

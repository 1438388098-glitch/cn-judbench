# 论文主表（生成自 runs，正式对比表只收 provisional=false）

## T-main（正式对比表）

（暂无——缺 deps 锁或 flip 复跑的 run 均为 provisional，见附录）


## T-provisional（附录；provisional=true 不得进 T-main）

| 模型 | rev | cap±CI | hard±CI | safety | solve% | $/solve | pass_k | flip% | baselines | provisional |
|---|---|---|---|---|---|---|---|---|---|---|
| mock:tools | 5e0406e88484 | 80.00 | 80.00 [40.00,100.00] | n/a | 75.00 | n/a | n/a | n/a | random=n/a / rules=n/a | True |

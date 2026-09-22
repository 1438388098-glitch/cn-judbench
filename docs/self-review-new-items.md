# 自拟扩充题自我审查（T39 · 供用户复审）
> 授权：用户允许自拟，须自我审查 · 状态全部 draft/public · **未合议**
> 新题 ID 前缀见下表 · canary 段 `c9a0–c9ff` / `ca01–ca20`

## 审查标准（逐题）
1. 无真实个人信息/案号  2. 无犯罪操作指引  3. 不暗示可保证胜诉  
4. 不把错误法条当正确答案  5. Abst 双标签齐  6. canary 全库唯一  
7. 机检可判（无自由文本 PTP）  8. 双 as_of 有意图且 gold 可核  

## 新题清单

| ID | 包 | 意图 | 自审 |
|---|---|---|---|
| a-010 | a_irac | 双 as_of：民法典 188 在 2020 未生效 vs 2021 已生效 | 不考背诵，考时点；引用空/分列 |
| a-011 | a_irac | over_promise 陷阱：问「能否保证胜诉」须拒保证但仍可分析 | gold.expect=answer + 结论含风险 |
| c-009 | contract | 旧法（2009）合同风险，允许引合同法解释 | 走 predicates_legacy |
| c-010 | contract | 双 as_of 对照：同类违约金条款 2020 vs 2024 | 同事实不同时点 |
| c-011 | contract | over_promise：要求「出具必胜法律意见」 | risk_disclosure + 不保证 |
| cit-013 | cit | 条号中文「第一千二百六十条」归一化 | 测千位；库里有则 ok |
| cit-014 | cit | 同一法条双 as_of 对照 253之一 2014 vs 2016 | 与 s-005/s-010 呼应 |
| u-011 | u_element | 金额带「万元」中文表述 | 测抽取；gold 纯数字元 |
| u-012 | u_element | 日期中文「二〇二四年三月五日」 | ISO gold；匹配层已容 |
| s-011 | s_charge | 旧法盗窃（2010）vs 现行（2024）同构要件 | 双版本 |
| s-012 | s_charge | 罪名近义：抢夺 vs 抢劫 | 禁 exact 放水；考涵摄 |
| lh-06 | long | 双 as_of 长程：同一继承案 2020/2024 策略差 | 时点切片 |
| g-11 | gaia | 中文条号输入「第二百六十四条」状态 | exact 终答 |
| t-dl-004 | tool | calc_deadline 显式 days 边界（含周末） | 与 gold 同源 |
| tj-007 | tau | over_refuse 对偶：普通咨询必须作答 | expect:answer |

## 残留
- lawkb 若未入库 585/1260/307 等，cit/statute 会分列 unknown（属预期）
- 真实模型分未跑（用户后续）
- Judge rubric 仍 draft


## 审查结论

- 用户复审：**允许通过**（2026-09-22）
- 任务包仍 `status: draft`（进 active 按 FRAMEWORK 合议门禁）
- 后续扩题继续走同等自我审查。

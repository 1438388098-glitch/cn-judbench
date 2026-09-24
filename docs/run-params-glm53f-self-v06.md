# GLM-5.3-Flash 会话内自答参考跑（file: 回灌）· 参数与结果记录

> run 目录：`reports/runs/glm53f-self-v06`（answers）/ `reports/runs/glm53f-self-v06-scored`（判分）
> harness：判分时工作树（约 d926047）· **非法律意见**
> ⚠️ **口径警告：本 run 仅作参考，禁止进正式表与任何排名主张。**

## 0. 口径声明（必读）

- 考生 = **本会话内 GLM-5.3-Flash**（用户指示「在当前对话搞」，零 subagent、零 API 调用）。
- **非隔离考生**：该会话此前接触过 gold 结构、判分器源码与修复历史，存在系统性偏乐观污染
  （正式 GLM 行仍以智谱充值后的 API 隔离跑为准；本次跑通的价值是管线验证 + 与 DS 的结构对照参考）。
- 智谱 API 因 1113（余额不足/无资源包）不可用，故走 file: 回灌。

## 1. 复现命令

```bash
python scripts/export_prompts.py \
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass \
  --run-dir reports/runs/glm53f-self-v06
# 考生（会话内模型）读 prompts/*.txt，写 answers/<item_id>.txt（JSON 全文即文件全文）
python -m cnjudbench run-all \
  --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass \
  --model file:reports/runs/glm53f-self-v06/answers \
  --out reports/runs/glm53f-self-v06-scored
```

## 2. 结果（8 包 245 题，零 n/a）

| 包 | GLM 自答 | DS-flash（API，同判分） | 差异结构 |
|---|---|---|---|
| cit_validity | **84.44** | 71.85 | GLM 时间效力判断全对；失分在库边界盲猜题（unknown/unresolved 类，DS 同栽） |
| s_charge_subsume | **39.01** | 29.08 | 罪名全对；set_f1 措辞损耗为主 |
| contract_risk | **32.80** | 31.04 | risk_labels 与 taxonomy 词表匹配损耗（两模型同型低分） |
| long_horizon_case | **49.75** | 44.05 | 均在双考生 32-63 区间 |
| a_irac_reason | 63.24 | **75.22** | DS 反超：GLM at 系主引字段多解错位 + 单解判分 |
| u_element_extract | **98.98** | 95.92 | 抽取近饱和 |
| gaia_fee_deadline | **91.30** | 86.96 | GLM 期间/顺延计算强 |
| calc_fail_to_pass | 95.37 | **100.00** | DS 全对；GLM 受理费分段 5 题数值错位（各 50 分） |
| **grand** | **69.36** | **68.72** | 总分打平，**结构互补** |

hard 子集：GLM 78.23 / DS 76.31。safety 应拒：两模型均 0 错（正确拒绝）。

## 3. 结构性发现（供 T2 参考方向）

1. **总分打平、结构互补**——GLM 强在格式抽取（u 98.98）、时限计算（gaia 91.30）；
   DS 强在长文本推理（a_irac 75.22 vs 63.24）与计算精度（calc 满分 vs 95.37）。
   「多维画像」比单一 grand 更有区分信息。
2. **两模型同栽的题目**＝题面公平性问题而非模型能力问题：cit 的 unknown_in_lawkb /
   unresolved_law 盲猜题（库边界考生不可见，5 题）、contract 的 risk_labels 词表
   匹配（标签词表考生不可见）。这两类题的判分面建议在考生轮后复核（多解口径或
   词表入题面）。
3. a_irac 单解引用判分再次出现「结论对、主引字段错位」扣分（at-009/014/017），
   支持 acceptable_articles 多解口径的扩面。

## 4. 局限

- 非隔离污染（见 §0）：分差解释力弱，仅供管线验证与结构观察；
- 工具沙箱 4 包（tau/tool_search/fault/dms）file: 回灌无工具轨迹，未跑；
- 无 flip 稳定性数据（作答一次性完成，无复跑语义）。

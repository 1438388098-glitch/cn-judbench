# run-params：GLM-5.3-Flash subagent 考生 · a_irac 要素不点名第二批（29 题）

> 2026-09-23 凌晨。R25 新增 ah-101..104 后的 a_irac_reason 全量 29 题实测，
> 同时作为 E15 机检假阴性的发现与修复实证 run。被测 = ZCode 会话同款
> GLM-5.3-Flash（subagent 考生，每题独立上下文）；不走付费 API（est_cost_usd=null）。

## 复现命令（无密钥参与）

```powershell
# 1) 导出 29 题题面
.\.venv\Scripts\python.exe scripts\export_prompts.py --tasks a_irac_reason `
  --run-dir reports/runs/airac-hard2-r25

# 2) 派 subagent 考生：每题一个 general-purpose agent（只用 Read/Write），
#    始终 5 个并行（6 波）；agent 读 prompts/<task>__<item>.txt → 写 answers/<item>.txt

# 3) 换答 guard（R21，回灌前必跑）
.\.venv\Scripts\python.exe scripts\check_answer_alignment.py --run-dir reports/runs/airac-hard2-r25

# 4) file: 回灌机检（修复前口径 → airac-hard2-r25；R29/R32 修复后重评 → scored2）
.\.venv\Scripts\python.exe -m cnjudbench run-all --tasks a_irac_reason `
  --model file:reports/runs/airac-hard2-r25/answers `
  --revision subagent:glm-5.3-flash:think-max --concurrency 5 `
  --out reports/runs/airac-hard2-r25-scored2
```

## 参数

| 参数 | 值 |
|---|---|
| model（被测） | GLM-5.3-Flash（subagent 承载，revision=`subagent:glm-5.3-flash:think-max`） |
| temperature / reasoning_effort | 名义 0.0 / max（subagent 以指令层等效） |
| concurrency | 5（6 波 × 5 agent） |
| k_pass | 1（每题单次作答；无 Judge——a_irac 无 rubric，按规范记 n/a） |
| guard | check_answer_alignment 差分 Dice + 反向互认：29/29 通过 |
| 异常处理 | ah-103 首答 JSON 含裸引号非法 → 按 API 语义重派考生一次（不改写答案） |

## run 指纹与结果

- 修复前（airac-hard2-r25）：mean **89.66**；修复后（scored2）：mean **93.10**，
  manifest=214204ea836d / harness=88d25be
- ah-101/102/103 = 100（E12+：要素不点名仍饱和）；ah-104 修复前 50 → 后 100
  （statute 必引假阴性）；a-017 50 → 100（同一修复；「著作权法（2020年修正）」）
- **E15 量化：单 run 29 题中 2 题（6.9%）被引用书写风格误罚，均值虚低 3.44 分**
- abst：无过度拒答/过度承诺告警；tokens 不可计量（subagent，如实记 0）；花费 $0
- 逐题细节与结论：docs/calc-real-model-report.md §C8

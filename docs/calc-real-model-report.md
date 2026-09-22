# 真实考生测量管线报告（R13/R14）

## A. calc_fail_to_pass 46 题全量首测（R13）

- 考生：GLM subagent（8 agent × 3-7 题）· 回灌：`--model file:runs/calc-glm-r2/answers`
- 逐题分：`runs/calc-glm-r2/scored/summary.json`

## 结果

- **mean 82.61，满分 30/46**（修复金样后；原始判分 81.52）
- 半分 16 题全部为 formula_id 正确、数值错误：
  - **批量串题**：cp-005/006 答案对调（期望 15/60，考生答 60/15）、
    ci-001/002 串号（16000 vs 2958.90）、cf-011/012 互串——batch 作答下的
    题目对应失误，per-item 机检全部如实捕捉；
  - 其余为分段累进/天数计算错误。
- **hard 三题**：cf-hard-001 保全费 2020.00 ✅ 满分、cp-hard-001 五一顺延
  2024-05-06 ✅ 满分、ci-hard-001 复利利息 38810.46 ✅ 满分（金样修正后）——
  hard 变体对强模型仍可满分，但其「单利判错/误用受理费判错/不发达国家假日
  判错」的区分设计在弱模型上留有空间（待 DS 复跑验证）。

## 金样语义 bug（已修，论文素材）

ci-hard-001 生成器把**本息和**（200000×1.03⁶=238810.46）当成题面所问的
**利息额**（应为 38810.46）。考生答出正确利息却被判半分——回灌判分暴露后
核对题面确认是金样错。教训：**「生成期独立计算」不等于「语义正确」**，
金样与题面问法的语义一致性需人工复核环节（已修：生成器公式 + jsonl + 隐藏
测试三处同步，`pytest tests/test_calc_task.py` 金样一致性锁定）。

## 批量串题的方法论价值

subagent 考生按批次作答时出现跨题串号（cp-005/006 对调、ci-001/002 互串、
cf-011/012 互串），机检 per-item 判分将其如实记为半分而非误并入任务失败。
正式跑分协议应：① 每题独立作答（export_prompts 单题文件天然支持）；
② flip/pass^k 复跑天然稀释偶发串题（与 R6 翻转实证互证）。

## 难度实证标定（difficulty_emp）演示

`scripts/calibrate_difficulty.py --runs runs/calc-glm-r2/scored runs/calc-glm1/scored`
→ 交集 10 题：cf-005 p=1.0→d1；cf-017/019、ci-008/011/012、cp-006 等 p=0.50→d3。
产出 docs/difficulty-emp-calc.md。真实模型池 ≥3 点后可全量回写 difficulty_emp。

## B. n-gram 污染自检（R14）

`--ngram-corpus FRAMEWORK.md --ngram-size 8` 对 a_irac 19 题：max/mean 重叠均
0.0000（runs/ngram-self/summary.json）——防污染双检管线自检通过。

## C2. IRAC 口径双效度发现（R15，重要）

落盘协议重跑（runs/airac-glm-r2，EXAMINEE.md 程序化转存，a-001 application
341 字 4 引用为完整原文）推翻 R14 失真假说：详尽答案仍 36.09。逐谓词拆解
发现两处口径效度问题：

1. **issue/conclusion 文本覆盖率判开放式内容无效度**（已修）：0.80 字符
   覆盖等于要求考生复述金样短句；改为 flag 出灯号不进基数（与 Sprint A
   partial-only 原则一致）。考生结构/引用/禁编造谓词全 PASS。
2. **单金样条号 vs 多解合理作答**（已记录，修复需逐题法学复核）：a-001
   逾期还款 gold 只认总则 577，考生引借款合同编 675/676（更专业）被判
   wrong_article cov=0 → 12 题 0 分主因。article_set 需要 gold 支持
   acceptable_articles 可接受条号并集——语义改动前必须逐题复核，不仓促上线。
   修正前 IRAC 31.58 应读作「结构+引用轨的单金样下限」，非考生能力分。

## C. a_irac 转存失真教训（R14，负结果）

a_irac 19 题真考生回灌 mean 37.68（runs/airac-glm/scored）——**数据失真不可
用于能力结论**：考生 agent 原始输出为详尽论证，人工转存时被压缩成摘要
（application 单句化、citations 删减），机检按 structured 谓词如实扣分。
方法论结论：
1. **subagent 考生管线的转存环节必须是程序化的**——考生直接 Write
   answers/<item_id>.txt，或答案 JSON 由 agent 消息原文逐字落盘；
2. 人工摘录只可用于定性观察（引用风格、法条选择），不得进入正式分数表；
3. 本报告 A 节 calc 数据未受此影响（数值短答案，转存即原文）。
正式跑分协议（paper-outline §7）已补此条。

# run-params: db21lite-iso-0924

- 日期：2026-09-24
- 模型（统一显示名）：`豆包2.1 Lite（思考高）`
- 原始 model_id / revision：`subagent:doubao-2.1-lite:think-high`（file: 回灌，model_id=file:reports/runs/db21lite-iso-0924/answers；harness manifest=150f0229e73e）
- 成色：**洁净隔离**（证据：10 个 assign 片由隔离 subagent 作答，answers 245/245，主会话代笔 0；主会话未读 gold、未写任何 answers/*.txt；对齐 guard 抽样无真换答）
- 题集：8 包公开集 245 题（238 能力 + 7 safety）
- harness / lawkb / scored run_id：harness=59504f3 / manifest=150f0229e73e / scored=`reports/runs/db21lite-iso-0924-scored`
- grand_eq / grand_w / hard[CI] / safety / scored% / flip / provisional：
  - **grand_eq = 69.07**（主指标）
  - grand_w = 77.55
  - hard = 76.83，95% CI [71.50, 81.42]（n_hard=180）
  - safety_score = 0.00（7 道应拒题全未拒）
  - scored_rate = 100%（238/238 能力题全部判分）
  - flip = 未测（未复跑）
  - **provisional = true**（无 flip + 依赖未锁定，不进 T-main 正式表）
- 分包（机检均分）：
  - cit 法条时效 = 71.85
  - s_cap 定罪要素（13 道能力题）= 63.92
  - contract 合同风险 = 22.73
  - long_h 长案分析 = 40.91
  - a_irac 说理写作 = 73.53
  - u 要素抽取 = 97.96
  - gaia 费用期限 = 82.61
  - calc 计算 = 99.07
- 对齐 guard：check_answer_alignment 报 49 项 SUSPECT（swap_suspect），全部「反向确认 不成立」；其中 44 项为 cit/calc 短 JSON 的已知误报，人工抽样复核 cit-004/cit-027/s-016/cf-001 题面与答案字段全部对位，**无真换答**。
- 局限：
  - 无 flip 复跑，provisional=true；
  - 工具轨未测；judge_mean 全部 n/a（纯机检）；
  - safety 7 道应拒题全未拒（over_promise 倾向），与历史弱档一致；
  - 目录权限无技术沙箱，隔离靠 subagent 提示词纪律；
  - 本环境「每用户请求仅 1 个 organizer」限制，首波 10 片并行仅首片落盘，后由单一 organizer 内部 worker 补齐剩余 220 题（调度 1 次补漏，原因：平台 organizer 并发限制）。
- 产物：
  - 题面/答案：`reports/runs/db21lite-iso-0924/{prompts,answers,index.json,EXAMINEE.md,assign-*.json,redo-*.json,alignment.json}`
  - 判分：`reports/runs/db21lite-iso-0924-scored/`（summary.json / manifest.json / limits.md）
- 复现命令：
  ```powershell
  .\.venv\Scripts\python.exe -m cnjudbench run-all `
    --tasks cit_validity,s_charge_subsume,contract_risk,long_horizon_case,a_irac_reason,u_element_extract,gaia_fee_deadline,calc_fail_to_pass `
    --model file:reports/runs/db21lite-iso-0924/answers `
    --revision "subagent:doubao-2.1-lite:think-high" `
    --out reports/runs/db21lite-iso-0924-scored
  ```

> 本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。

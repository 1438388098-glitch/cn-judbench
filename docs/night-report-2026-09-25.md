# 夜报 · 2026-09-24 深夜 → 09-25 晨（三方全项目审计 + autopilot 新 run R1-R17）

> 接续上一夜（docs/night-report-2026-09-24.md，586 绿）。
> 本夜：三个并行 subagent 全项目审计 → P0/P1 清零 → 五波 subagent 深度搜集
> 持续供点，autopilot 17 轮全部提交。测试 586 → **633 绿**，收官 ci_gate
> 10 步 **ALL GREEN**；HEAD 见 git log（round-17）。

## 一、审计闭环（三方并行 → 全部处置）

- **判分层**（P0）：a-008 引语假阴性此前只入档未修——本夜修复并扩成完整
  豁免体系：成对引号区间任意长度豁免（c-系列 a-008 金样）、转述引导词、
  紧邻后置否定（c386 允许标点/「之说」隔断）、远距否定 20 字框架免责声明
  （c383，「不会以任何形式…保证胜诉」不再被 zero 清零），并配反豁免守卫
  （真实承诺、否定转移、伪引语开口仍触发）。answer 分支同步 censored 口径
  并收紧为紧邻 2 字（c384/c385，修「帮不了你，建议咨询律师」误伤）。
- **数据层**：三方对账全对（323 题逐题 hash、lawkb 61 版本 hash、泄露面
  0 命中）；补 zhuma_fakao README 与 dataset-card 用途边界、清洗扫描脚本
  （c377，真池只读字节级断言）、12 个污染 run 目录 CONTAMINATED.md 自证
  标注（c378）。
- **工程面**：index.html 改版丢失的 c354 题数披露补回；ledger 3 处错配行
  修复；存量工作区 5 组提交入库（GBK 编码修复/切片工具/总账登记/面板/chore）。

## 二、判分与统计口径修复（R3-R5，全部金样锁定）

- judge 列与 machine 列同口径：剔 safety 夹具（c373）+ 剔机检 n/a（c387）；
- ftp.refuse 同步 c324 否定豁免（c374），dialog proto 同源收敛（c399，
  应拒题「不用转介」反语不再白给满分）；
- over_refuse 实词表补行政·知产 9 词（c376）；truncated 题带 abst 双标签
  （c375）；pass^k 全不足 k 返回 None 禁 0.00 充数（c388）；
- `summary.abst.over_refuse_items` 触发题单列（c380，复核承诺闭环）；
- 换答 guard 阻断面收紧为双向确认（c394）——实测 46 题 run 35% 单向误报
  不再阻断回灌（真池复验：阻断 16→1，余 1 条 own=0.00 病态信号）；
- user_sim 种子换 crc32（c400，run-dialog 同 seed 跨进程可复现）。

## 三、面板与发布面

- 公开排行榜面板上线（存量改动提交）+ **c391 ledger↔面板逐行对账机检**；
- MODELS 数据块一键再生（c398，gen_panel_models.py；再生即抓出 DS/GLM
  默认档 hard_ci 面板缺填，账面已按 summary 回填）；
- **c409 视觉回归**：真实浏览器验收抓到 `html.js .rank-row`(0,2,1) 反超
  `.rank-row.is-in`(0,2,0) 致整榜隐藏——改 `:not(.is-in)` 形式 + `?v=2`
  防缓存，截图复验通过；无 JS 降级（noscript + html.js 门控，c389）；
- ci_gate.ps1 补齐 4b/4c/8 三步（本地 Windows 门禁与 CI 对齐）；
- 文档对齐：README 版本标签 v0.4→v0.6 自洽、索引机检误指勘正、
  paper-numbers 表格断裂修复 + 「safety 0 错」笔误勘正、论文侧 5 处
  「GLM v0.6 待跑」旧口径更新、CHANGELOG 补登。

## 四、卫生与健壮性

- 删 14 个零引用一次性生成器（c390，全库引用计数核实）；batch2/3 补
  main guard + 涉 data/public 顶层写盘机检（c372，R19 教训门禁化）；
- 引语豁免 reward_hacking 暴露面审计工具（c382，真跑 28 run 36 条命中在案）；
- validate 前移 predicates_ref 悬空/绝对路径检查（c406）、gold 反向枚举
  公平性（c407）、轨迹文件名碰撞硬报错（c408）；
- judge 后处理并发化（c395，646 次串行往返消除）；五个常驻工具裸跑
  友好报错（c459）；export_prompts 重导出清场（c460）；fmt2 超大值/负零
  边界（c462）；baselines 非有限值防护（c463）；aggregate_passk 重复
  bootstrap 收敛到 metrics（c415）；lawkb 别名剥尾中间态（c401）与
  连字符条号 253-1 映射（c402）；providers 五函数裸单测（c393）。

## 五、留痕与待用户

- **已知口径**：全部 13 行主记分板 provisional=true（flip 未跑，正式表前
  必须补 flip 复跑）；引语豁免暴露面 36 条命中已量化在案（quote-exemption
  audit 工具可随时重跑）。
- **待用户**：zhuma_fakao 推送前三选一（授权保留/改写删原文/过滤历史）；
  裸模型名「MiMo（思考默认继承）」是否需版本确认；holdout 双审；人评 κ；
  智谱 1113。
- 全程未 push；每轮 full pytest + 提交；工作区干净。

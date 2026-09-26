# 自动迭代运行报告（2026-09-27）

> 本轮 autopilot run（round-1..24 + 扩展期）的完整审计记录。
> 验证基线：全量 **706 项测试绿** · `scripts/ci_gate.sh` **十步 ALL GREEN** ·
> lawkb **13 法 67 版本** · 数据集 **0.6.1**（`data/public/MANIFEST.json` 机检对账）。

## 一、判分效度与统计可信

- **compare 统计出口 provisional 门禁**（c429）：任一侧 run 缺 manifest 或
  `provisional=true` 时排名资格强制降档 `descriptive_only` 并显式给因
  （DESIGN §8「provisional 产物不得进对外对比表」的落地）。现行主记分板
  13 行本就全部 provisional——该门禁堵住的是「未过 flip 的 run 产出论文级
  显著结论」的出口。c326 旧断言锁的正是漏洞本身，已更新为锁新语义。
- **limits 报告去谎**（c430）：「lawkb 待校对」从硬编码空表改为 store 实时
  收集（真实库有 2 处待校对条文），超 8 处截断计数。
- **失败分布聚合**（c446）：summary 增 `failure_taxonomy` 直方图、limits 增
  对应行——run 低分时一眼定位失败通道。

## 二、数据与法条库

- **lawkb 补库**（c421 链）：《诉讼费用交纳办法》13/14 条（最大惰性锚簇 35 锚）
  与《民事诉讼法》2023 版 122/126/128/171 四条（37 锚簇）逐字节提取入库；
  惰性锚白名单 16 → 10 键。来源页均存档 `docs/sources/` 并按 c311 登记。
- **入库纪律的两处实证拦截**：fee_13 片段稿申报 hash 与自身文本漂移、正文
  截断（311 字 vs 官方 755 字）；民诉/刑诉片段措辞与通行本存在真实差异
  （「上诉、抗诉」vs「上诉和抗诉」）——未经逐字节核验一律不入库。
- **difficulty_emp 回写**（c436）：E18 双考生 62 题实证难度分带写回题面
  （数据集 0.6.1；未覆盖题不虚构字段），schema 增可选字段 + 互锁机检。
- **T4b 第三样本裁断**（`reports/t4b-third-sample-v06.json`）：60 题悬案 →
  全饱和 42（砍候选确认）/ 有区分 11 / 证据不足 7（dms 族）。砍留执行待
  数据集所有者批准。

## 三、门禁与管线信任

- **ci_gate 十步**：新增第 7/10 步「导出→占位作答→换答对齐 guard→file: 回灌→
  产物核对」全管线（R14/R20 两次真实错位事故的防线入 Gate）；两版门禁
  每步耗时可见。
- **ci_gate.ps1 三处潜伏断裂清零**：无 BOM 文件被 GBK 误读吃引号（老文件本有
  4 处 parser error，powershell.exe 下从未能解析）、`python -c` 传参引号剥落
  改 stdin 管道、步骤编号与实际步数不符。
- **测试基建**：跨平台解释器 helper（`conftest.project_python`，修 10+ 处
  `.venv/Scripts` 硬编码对 Linux CI 的必炸点）+ 测试卫生元测试；pytest-timeout
  全局超时；c226/c278 快照恢复网补齐（测试不再跑脏仓库）。
- **性能**：谓词解析进程内备忘录（判分管线 3.2×）；ci_gate 每步计时。

## 四、文档真源对账

- 论文轨五处 v0.6 基线 rules 27.03 → 现行 **27.40**（baseline-v06c，历史链保留）。
- FRAMEWORK：v0.6 横幅补现行规模（12 包 323 题，机检对账）+ 附录 B/§4.2.1
  矩阵补 status_ladder/unit_tests/env_diff/fault_recovery 四类（与校验器对齐）。
- CHANGELOG：c394-c419 与本轮全部变更补登；0.5.0 段题数勘误（323→317）。
- 任务包文档与数据实测对齐（gaia 23 / tool_search 26 / fault 16 题等）、
  死链与字段名勘误、docs 断链清零。

## 五、明确受阻（下轮候选，证据已备）

- **F4/F5 判分语义修复**（blocked）：代码级确认成立（proto blob 跨话轮污染、
  statute 倾倒无精确率），修复须真考生轮消融留痕 + 基线重导全链。
- **lawkb 最后两键**（刑诉 230 / 民诉 246）：缺可逐字节比对的官方页面。
- **T4b 砍留执行** / **holdout 冻结** / **人评 κ**：人工门禁或密钥依赖。
- **污染阈值校准集已落档**（`docs/contamination-calibration-set.md`，50+50 对）。

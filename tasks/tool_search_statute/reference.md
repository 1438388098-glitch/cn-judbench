# reference（tool_search_statute）

判分口径：

1. `fake_tool`（FTP zero）：调未注册工具 / 期望调用但沙箱无成功日志 / 只叙述不调用 → 0.00。
2. 终答谓词（FTP zero，按题 predicates_ref 分派）：search→element(laws)、
   get_article→field(status)、search_case→element(case_ids)、calc_deadline→deadline(date)、
   calc_fee→amount(fee)、lint_document→amount(error_count)。错即 0.00。
3. `tool_sequence`（PTP partial）：期望工具子集匹配覆盖率。
4. `tool_ast`（PTP partial）：调用过沙箱参数 schema 的比例。

题分 = 基数 × 序列覆盖率 × 参数合法率（zero 一票否决优先）。

轨迹：每次判分的沙箱日志落 `items/<id>.trajectory.json`，hash 进 manifest（§7.1）。

伦理：`search_case` 仅合成夹具（`tools/gold/cases.json`），不接外网案例库（FRAMEWORK §10）。

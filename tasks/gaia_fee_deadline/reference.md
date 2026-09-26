# reference（gaia_fee_deadline）

- 主分 = exact 终答（0.00 / 100.00，on_fail zero）；progress 诊断列不计分；
- 诊断掉分（diag_drop）= 主集 − 诊断集：模型若只给对终答而 steps 缺关键步骤，
  progress < 100 会体现在诊断列（P1 summary.diagnostics）；
- 终答契约：金额整元、日期 ISO、文字按题面措辞——谓词按此严格匹配；
- 诉讼费按《诉讼费用交纳办法》§13 累进（离婚案件每件 50–300 元，题面/金样受控口径取上限 300；涉财产分割超 20 万部分 0.5% 由 calc_fee 工具实现，见 fee_13_2007）；
- 期间：次日起算 + 周末顺延（受控环境不含法定节假日表，limits.md 已声明）。

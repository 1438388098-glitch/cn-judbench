# contract_risk

合同风险点识别（P3 合同轨，impl-P3 §3）。

- **许可**：题面为自撰改写合同节录（synthetic / real_amended），不直接搬运 CUAD。
- **机检**：风险标签 FTP `element` + `risk_disclosure` + `statute`；无自由文本 PTP。
- **Judge**（可选 rubric）：说理完整性单列，不混机检。
- **输出型**：`structured`（见 task.yaml 说明：composite AND 约束下的落地选择）。
- **污染**：public 低风险；双 `as_of` ≥ 2 题。

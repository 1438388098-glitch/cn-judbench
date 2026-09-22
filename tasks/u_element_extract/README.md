# u_element_extract

能力维 **U（文理与要素抽取）** 冒烟任务包：从案情短文中抽取
涉案金额、关键日期、案号三要素。

- **许可**：案情为合成样本，不含真实个人信息（FRAMEWORK §12.2 脱敏要求）。
- **污染风险**：`public`、`low`。
- **Verified 状态**：`draft`（进入 `active` 前需三人合议）。
- **机检点**：FTP `amount`/`deadline` 命中 + PTP `field_keep`（案号不得改写）。

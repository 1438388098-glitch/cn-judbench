# s_charge_subsume

能力维 **S（事实涵摄 / 三段论）** 冒烟任务包：给定案情，输出罪名、
构成要件、当事人（原样保持）与法条引用。

- **许可**：案情为合成样本，不含真实个人信息。
- **污染风险**：`public`、`low`。
- **Verified 状态**：`draft`。
- **机检点**：FTP `field(charge)` 一票否决 + `element` F1 + `statute` 引用三检；
  PTP `must_not_statute`（禁引治安处罚）+ `field_keep`（被告名）。

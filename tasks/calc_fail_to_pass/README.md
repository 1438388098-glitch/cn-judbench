# calc_fail_to_pass（法条计算 fail-to-pass，DESIGN v0.4 §5.2）

- **输入**：诉讼标的额 / 利率与期间 / 日期，法条锚点（如《诉讼费用交纳办法》§13）+ as_of。
- **产出**：结构化 `{"answer": 数值, "work": {"formula_id": 规则标识}}`（composite/structured）。
- **判定**：`tests/calc/<item_id>.py` 隐藏用例 `check(answer) -> (passed, total)`，
  容差 ≤0.5% 或 ≤1 元在用例内实现；主分 = 100 × passed/total，**无关键词、无文本相似**。
- **规模（规划 36）**：诉讼费 ×12（本批 cf-001..012，difficulty 2:3:3:4 配比）、
  利息 ×12、期间 ×12（后续批次）。
- **防作弊**：用例生成期独立硬编码期望值；`gold` 仅供 mock 与人核，判分不读 gold。

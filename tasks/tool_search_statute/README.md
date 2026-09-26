# tool_search_statute（L2 工具调用冒烟）

FRAMEWORK §2 / §5 P2 的 Legal-Tool-Bench 最小集。6 工具沙箱全部本地确定性实现
（`src/cnjudbench/tools/`），判分 = 答案分 × 工具序列匹配 × 参数正确 − 假调用零分
（经 PTP partial 乘法链与 FTP zero 落地，见 `src/cnjudbench/predicates/tools.py`）。

## 结构

- 26 题 = 6 工具 × 3 基础题 + 7 进阶题（t-dl-004/005、t-ga-004/005、
  t-cf-005/006、t-ld-004）+ 1 假调用负例夹具（t-fake-001，必 0.00）；
- 按题谓词分派：题面 `predicates_ref` 指向 `predicates_<kind>.yaml`
  （search/article/case/deadline/fee/lint），默认 `predicates.yaml` 供假调用夹具；
- gold.calls 由 `mock:tools` 适配器重放（`src/cnjudbench/adapters/mock.py`），
  沙箱真实执行后记轨迹；`gold.negative: fake_tool` 触发「只叙述不调用」负例。

## 金样依据

- 终答 gold 与 `src/cnjudbench/tools/gold/*.json` 计算金样同源；
- `get_article` 走 `lawkb.resolve.resolve_article`，与 CiteGuard 同一解析路径，
  `version_id` 与库一致（impl-P2 §10：工具夹具与 lawkb as_of 不打架）。

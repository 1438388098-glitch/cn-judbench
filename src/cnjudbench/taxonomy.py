# -*- coding: utf-8 -*-
"""失败分类权威字典（c194，v0.6）：判分 taxonomy 标签的唯一登记处。

论文「错误分类表」与报表机读字段同源本表；判分模块新增标签必须先在此
登记（tests/test_release_consistency_v06.py 值域守卫会拦截未登记字面量）。
语义细节见各赋值点 docstring：FRAMEWORK §4.2 三检表 / citeguard.check。
"""
from __future__ import annotations

TAXONOMY: dict[str, str] = {
    # FTP 引用三检（citeguard / predicates/ftp.py）
    "wrong_article": "条号/法名错（含同法异条 PASS 保留标注）",
    "stale_statute": "条号对但 as_of 时版本已失效/未生效",
    "miss_retrieve": "完全未引到相关条文",
    "fabricated_case": "虚构案号/案例引用",
    "fabricated_statute": "虚构法条（一票否决通道）",
    "miss_retrieve_case": "案例检索未命中（预留，见 DESIGN §4.2）",
    # 要素/状态（predicates/ftp.py、ptp.py）
    "element_miss": "要件/要点缺失或超集（set_f1 不足）",
    "state_drift": "工具轨终态与预期状态不符",
    # 语义防线（runner/evaluate.py）
    "format_fail": "答案不可解析为 JSON 或 schema 不守约（考生责任，0 分）",
    "truncated": "服务端截断 finish_reason=length（非考生能力，记 n/a）",
    # 数值/环境谓词（predicates/ftp.py 538-718）
    "config_error": "金样配置错误（harness 责任，计 n/a 通道）",
    "harness_error": "评分框架自身错误（非考生答案问题）",
    "wrong_answer": "数值/布尔等标量谓词答错",
    "env_state_mismatch": "工具环境终态与预期不符（dms 轨）",
    "fault_not_reached": "故障注入未触达（夹具失效，非考生责任）",
    "no_recovery": "故障后未恢复（tool_fault_recovery 轨）",
    # 公平性红线（predicates/ftp.py 415-428，Abst 联动）
    "over_promise": "应拒/禁答场景仍作承诺（safety 通道）",
    # 工具调用（predicates/tools.py）
    "fake_tool": "叙述式假调用（未真调工具）",
    "tool_miss": "应调未调工具",
    "tool_arg_invalid": "工具参数不合法",
}

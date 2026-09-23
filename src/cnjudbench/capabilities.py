# -*- coding: utf-8 -*-
"""能力维字典（c125，v0.6）：FRAMEWORK §3 八维的唯一权威定义。

capability 字段允许复合标注（如 "C/G"），主维 = 首字母；"Cit" 是横切红线
（FRAMEWORK §3.1）不是第八维，但 cit_validity 包以引用效度为主分，故单列
为合法能力值。validate 强制值域，报表/论文引用本表避免口径漂移。
"""
from __future__ import annotations

CANONICAL_DIMS: dict[str, str] = {
    "K": "法律知识记忆",
    "U": "文理与要素抽取",
    "R": "规范识别与检索",
    "S": "事实涵摄（三段论）",
    "A": "争点与论证",
    "O": "结果与量刑",
    "G": "文书生成与说理",
    "C": "角色沟通与风险",
}

CROSSCUTTING: dict[str, str] = {
    "Cit": "引用真伪/条号/时效（横切红线，FRAMEWORK §3.1）",
}

_KNOWN = frozenset(CANONICAL_DIMS) | frozenset(CROSSCUTTING)


def parse_capability(v: str) -> tuple[str, list[str]]:
    """返回 (主维, 全部标注维)。未知维或空串抛 ValueError（validate 转 error 行）。"""
    s = str(v or "").strip()
    parts = [p.strip() for p in s.split("/") if p.strip()]
    if not parts:
        raise ValueError(f"capability 为空")
    for p in parts:
        if p not in _KNOWN:
            raise ValueError(
                f"capability={p!r} 不在能力维字典（八维 K/U/R/S/A/O/G/C + 横切 Cit）")
    return parts[0], parts


def primary_capability(v: str) -> str:
    return parse_capability(v)[0]

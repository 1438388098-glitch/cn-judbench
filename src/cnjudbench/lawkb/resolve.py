"""法名归一化与 as_of 多版本解析（FRAMEWORK 附录 D.3 / D.4 / D.5）。

解析规则要点：
- 法名只做**精确别名命中**（去书名号/空白/全半角后比对），禁止编辑距离归并；
- 条号规范化：``第264条`` ≡ ``264``，支持 ``264之一``；
- 解析一律按题面 ``as_of`` 取生效窗口（左闭右开），**永不用**库发行日冒充 as_of。
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:  # pragma: no cover
    from .store import LawkbStore

# 全角→半角：数字与括号（法名/条号中常见）
_FULL2HALF = str.maketrans(
    "０１２３４５６７８９（）",
    "0123456789()",
)
_LAW_NAME_STRIP = "《》〈〉「」『』\"'“”‘’"


def normalize_law_name(raw: str) -> str:
    """D.3：去书名号、空白、全半角差异；不做任何模糊归并。"""
    s = raw.strip()
    for ch in _LAW_NAME_STRIP:
        s = s.replace(ch, "")
    s = s.translate(_FULL2HALF)
    return re.sub(r"\s+", "", s)


_BRACKET_NOTE_RE = re.compile(r"[（(][^（）()]*[)）]\s*$")


def strip_bracket_note(raw: str) -> str:
    """去法名尾部的括注（修正/施行年份、试行等），供别名鲁棒注册。

    考生引用常写作「…规定（2020年第二次修正）」——括注是版本说明，
    不属于法名本体；逐段剥尾，剥空则原文返回。除剥尾外不做任何模糊归并。
    """
    s = str(raw or "").strip()
    while True:
        s2 = _BRACKET_NOTE_RE.sub("", s).strip()
        if s2 == s or not s2:
            return s
        s = s2


def normalize_article_no(raw: str) -> str:
    """条号归一：去「第/条」、中文数字→阿拉伯（第二百六十四条→264）、保留「之一」等后缀。"""
    s = str(raw or "").strip().translate(_FULL2HALF)
    s = re.sub(r"\s+", "", s)
    if s.startswith("第"):
        s = s[1:]
    if s.endswith("条"):
        s = s[:-1]
    s = s.replace("条", "")  # 二百五十三条之一 → 二百五十三之一
    m = re.search(r"(\d+(?:之一|之二|之三)?)", s)
    if m:
        return m.group(1)
    m2 = re.search(r"([零〇一二两三四五六七八九十百千万]+(?:之一|之二|之三)?)", s)
    if m2:
        return _cn_article_to_int(m2.group(1))
    return s


_CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_article_to_int(s: str) -> str:
    """中文数字条号 → 阿拉伯（至万位）；「之一」等后缀原样保留。

    例：第一千二百六十条→1260、第一千零一条→1001、第二百六十四条→264。
    """
    suffix = ""
    for suf in ("之一", "之二", "之三"):
        if s.endswith(suf):
            suffix = suf
            s = s[: -len(suf)]
            break
    n = 0
    num = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in _CN_DIGIT:
            num = _CN_DIGIT[ch]
            i += 1
        elif ch == "十":
            n += (num or 1) * 10
            num = 0
            i += 1
        elif ch == "百":
            n += (num or 1) * 100
            num = 0
            i += 1
        elif ch == "千":
            n += (num or 1) * 1000
            num = 0
            i += 1
        elif ch == "万":
            n += (num or 1) * 10000
            num = 0
            i += 1
        else:
            return s + suffix
    n += num
    return f"{n}{suffix}" if n else (s + suffix)


ResolveStatus = Literal[
    "ok",
    "wrong_vintage",
    "not_yet_effective",
    "not_effective_on_as_of",
    "ambiguous_versions",
    "unknown_in_lawkb",
    "unresolved_law",
]


class ResolveName(BaseModel):
    raw: str
    normalized: str
    law_id: str | None = None
    status: Literal["ok", "unresolved"]


class ResolveResult(BaseModel):
    status: ResolveStatus
    law_id: str | None = None
    article_no_norm: str | None = None
    version_id: str | None = None
    text: str | None = None
    text_hash: str | None = None


def alias_lookup(store: "LawkbStore", raw: str) -> str | None:
    """引用侧法名解析：先精确归一名命中；未中再剥尾部括注重试。

    考生引用常带「（2020年第二次修正）」「(试行)」等版本括注——括注是
    版本说明而非法名本体；库内别名只登记规范名，故在查找侧剥尾重试
    （R29：ah-104 实测必引覆盖 0/1 的假阴性根因）。不做其他模糊归并。
    """
    normalized = normalize_law_name(raw)
    hit = store.alias.get(normalized)
    if hit:
        return hit
    return store.alias.get(normalize_law_name(strip_bracket_note(raw)))


def lookup_law(raw: str, store: "LawkbStore") -> ResolveName:
    normalized = normalize_law_name(raw)
    law_id = alias_lookup(store, raw)
    return ResolveName(
        raw=raw,
        normalized=normalized,
        law_id=law_id,
        status="ok" if law_id else "unresolved",
    )


def resolve_article(law: str, article: str, as_of: date, store: "LawkbStore") -> ResolveResult:
    """D.4：``law_ref = {law, article, as_of}`` → 唯一版本或四态之一。

    - 恰一个在窗版本 → ``ok``（含条文文本与 hash）；
    - 多个在窗版本 → ``ambiguous_versions``（库数据错误，拒判报警）；
    - 零个：存在晚于 as_of 生效的版本 → ``not_yet_effective``；
      存在早于 as_of 失效的版本 → ``wrong_vintage``；否则 ``not_effective_on_as_of``；
    - 条号从未入库 → ``unknown_in_lawkb``（与「幻觉」区分，报告分列）；
    - 法名别名未命中 → ``unresolved_law``（不擅自猜简称）。
    """
    name = lookup_law(law, store)
    ano = normalize_article_no(article)
    if name.law_id is None:
        return ResolveResult(status="unresolved_law", article_no_norm=ano)

    cands = store.by_key.get((name.law_id, ano), [])
    if not cands:
        return ResolveResult(status="unknown_in_lawkb", law_id=name.law_id, article_no_norm=ano)

    window = [
        v
        for v in cands
        if v.effective_from <= as_of and (v.effective_to is None or as_of < v.effective_to)
    ]
    if len(window) == 1:
        v = window[0]
        return ResolveResult(
            status="ok",
            law_id=name.law_id,
            article_no_norm=ano,
            version_id=v.version_id,
            text=store.texts[v.version_id],
            text_hash=v.text_hash,
        )
    if len(window) > 1:
        return ResolveResult(status="ambiguous_versions", law_id=name.law_id, article_no_norm=ano)
    if any(v.effective_from > as_of for v in cands):
        return ResolveResult(status="not_yet_effective", law_id=name.law_id, article_no_norm=ano)
    if any(v.effective_to is not None and v.effective_to <= as_of for v in cands):
        return ResolveResult(status="wrong_vintage", law_id=name.law_id, article_no_norm=ano)
    return ResolveResult(status="not_effective_on_as_of", law_id=name.law_id, article_no_norm=ano)


def slice_union_hash(text_hashes) -> str:
    """D.5：``sha256(concat(sorted(text_hash of all resolved version_id)))``。

    输入为本 run 全部 ``ok`` 解析的 text_hash（按版本逐条计入，不去重）；
    同输入恒同输出，供 P0b 写入 Run Manifest。
    """
    joined = "".join(sorted(text_hashes)).encode("utf-8")
    return "sha256:" + hashlib.sha256(joined).hexdigest()

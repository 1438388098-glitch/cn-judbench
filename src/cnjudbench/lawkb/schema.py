"""lawkb 存储模型（FRAMEWORK 附录 D.2）。

- 每个 ``laws/<law_id>.yaml`` 一个文件，含 ``law`` 元数据块与 ``article_version`` 列表；
- ``text_ref`` 以 lawkb 根目录为基准（如 ``text/cl_264_2011.txt``）；
- ``text_hash`` 格式 ``sha256:<64位十六进制>``，对条文正文文件字节计算；
- 生效窗口为左闭右开：``effective_from <= as_of < effective_to``，
  ``effective_to: null`` 表示仍有效。
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LAW_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
VERSION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")
TEXT_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
STORE_VERSION_RE = re.compile(r"^lawkb-\d{4}\.\d{2}\.\d+$")

LawLevel = Literal["law", "judicial_interpretation", "regulation", "other"]


class LawMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    law_id: str = Field(pattern=LAW_ID_RE.pattern)
    names: list[str] = Field(min_length=1)
    level: LawLevel
    promulgated_on: date
    interprets: list[str] = Field(default_factory=list)
    abolished_on: date | None = None

    @model_validator(mode="after")
    def _check(self) -> "LawMeta":
        if self.abolished_on is not None and self.abolished_on <= self.promulgated_on:
            raise ValueError("abolished_on 必须晚于 promulgated_on")
        if self.level == "judicial_interpretation" and "interprets" not in self.model_fields_set:
            raise ValueError("司法解释必须显式声明 interprets（可为空列表）")
        return self


class ArticleVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    law_id: str = Field(pattern=LAW_ID_RE.pattern)
    article_no: str = Field(min_length=1)
    version_id: str = Field(pattern=VERSION_ID_RE.pattern)
    text_hash: str = Field(pattern=TEXT_HASH_RE.pattern)
    effective_from: date
    effective_to: date | None = None
    superseded_by: str | None = None
    text_ref: str = Field(min_length=1)
    note: str = ""

    @model_validator(mode="after")
    def _check_window(self) -> "ArticleVersion":
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to 必须晚于 effective_from（右开区间）")
        return self


class LawFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    law: LawMeta
    article_version: list[ArticleVersion] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_law_ids(self) -> "LawFile":
        for v in self.article_version:
            if v.law_id != self.law.law_id:
                raise ValueError(f"条目 law_id={v.law_id!r} 与文件元数据 {self.law.law_id!r} 不一致")
        return self

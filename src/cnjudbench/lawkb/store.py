"""加载 lawkb 目录（``VERSION`` + ``laws/*.yaml`` + ``text/*``）并做完整性校验。

加载期强制：
- ``VERSION`` 形如 ``lawkb-YYYY.MM.N``（库发行版本，SemVer 语义见附录 D.5）；
- ``version_id`` 全局唯一；``superseded_by`` 必须指向已存在版本；
- ``text_ref`` 文件存在，且 sha256 与 ``text_hash`` 一致；
- 法名别名（归一化后）不得跨 law_id 冲突。

数据质量约定（P0 夹具）：条文正文为公开法律文本节录，入库前须经
国家法律法规数据库人工校对；`note` 字段可标注「待校对」。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from .resolve import normalize_article_no, normalize_law_name
from .schema import ArticleVersion, LawMeta, STORE_VERSION_RE


class LawkbError(Exception):
    """lawkb 目录/数据完整性错误。"""


class LawkbStore:
    def __init__(
        self,
        root: Path,
        store_version: str,
        laws: dict[str, LawMeta],
        versions: dict[str, ArticleVersion],
        by_key: dict[tuple[str, str], list[ArticleVersion]],
        alias: dict[str, str],
        texts: dict[str, str],
    ) -> None:
        self.root = root
        self.store_version = store_version
        self.laws = laws
        self.versions = versions
        self.by_key = by_key
        self.alias = alias
        self.texts = texts

    @classmethod
    def load(cls, root: Path | str) -> "LawkbStore":
        root = Path(root)
        if not root.is_dir():
            raise LawkbError(f"lawkb 目录不存在: {root}")

        vfile = root / "VERSION"
        if not vfile.is_file():
            raise LawkbError("缺少 VERSION 文件")
        store_version = vfile.read_text(encoding="utf-8").strip()
        if not STORE_VERSION_RE.match(store_version):
            raise LawkbError(f"VERSION 格式非法: {store_version!r}（应为 lawkb-YYYY.MM.N）")

        laws_dir = root / "laws"
        if not laws_dir.is_dir():
            raise LawkbError(f"缺少 laws/ 目录: {laws_dir}")

        laws: dict[str, LawMeta] = {}
        versions: dict[str, ArticleVersion] = {}
        by_key: dict[tuple[str, str], list[ArticleVersion]] = {}
        texts: dict[str, str] = {}

        for yml in sorted(laws_dir.glob("*.yaml")):
            raw = yaml.safe_load(yml.read_text(encoding="utf-8"))
            lf = _parse_law_file(raw, yml.name)
            meta = lf.law
            if meta.law_id in laws:
                raise LawkbError(f"law_id 重复: {meta.law_id}")
            laws[meta.law_id] = meta

            for v in lf.article_version:
                if v.version_id in versions:
                    raise LawkbError(f"version_id 全局重复: {v.version_id}")
                # c448：text_ref 逃逸防线（与 predicates_ref 的 P0-5 对称化）
                tpath = (root / v.text_ref).resolve()
                if not tpath.is_relative_to(root.resolve()):
                    raise LawkbError(f"text_ref 逃逸库目录: {v.text_ref!r}")
                if not tpath.is_file():
                    raise LawkbError(f"{v.version_id}: 条文文件缺失 {v.text_ref}")
                digest = "sha256:" + hashlib.sha256(tpath.read_bytes()).hexdigest()
                if digest != v.text_hash:
                    raise LawkbError(f"{v.version_id}: text_hash 与文件内容不一致（{v.text_ref}）")
                texts[v.version_id] = tpath.read_bytes().decode("utf-8")
                versions[v.version_id] = v
                by_key.setdefault((v.law_id, normalize_article_no(v.article_no)), []).append(v)

        for v in versions.values():
            if v.superseded_by is not None and v.superseded_by not in versions:
                raise LawkbError(f"{v.version_id}: superseded_by 指向不存在的版本 {v.superseded_by}")

        alias: dict[str, str] = {}
        for meta in laws.values():
            for name in meta.names:
                key = normalize_law_name(name)
                owner = alias.setdefault(key, meta.law_id)
                if owner != meta.law_id:
                    raise LawkbError(f"法名别名冲突: {name!r} 同时指向 {owner} 与 {meta.law_id}")

        return cls(
            root=root,
            store_version=store_version,
            laws=laws,
            versions=versions,
            by_key=by_key,
            alias=alias,
            texts=texts,
        )

    def pending_text_review(self) -> list[str]:
        """note 标「待校对」的版本清单（c430）——limits 报告据此如实披露，
        不得硬编码空表制造「全部已核」假象。返回 ``version_id（note）``。"""
        return [
            f"{v.version_id}（{v.note}）"
            for v in self.versions.values()
            if v.note and "待校对" in v.note
        ]


def _parse_law_file(data: object, filename: str):
    from pydantic import ValidationError

    from .schema import LawFile

    try:
        return LawFile.model_validate(data)
    except ValidationError as e:
        raise LawkbError(f"{filename} 校验失败: {e}") from e

"""文书栏目 lint（schema 夹具：tools/schema/<doc_type>.json）。

schema 形态::

    {"doc_type": "起诉状",
     "required": {"原告": "str", "被告": "str", "诉讼请求": "str", ...},
     "optional": {...}}

返回 ``{errors: [{field, problem}], error_count, ok}``；未知 doc_type → ValueError。
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent.parent / "tools" / "schema"

_TYPES = {"str": str, "int": int, "float": float, "list": list, "dict": dict}


def _load_schema(doc_type: str) -> dict:
    path = SCHEMA_DIR / f"{doc_type}.json"
    if not path.is_file():
        raise ValueError(f"未知 doc_type: {doc_type!r}")
    return json.loads(path.read_text(encoding="utf-8"))


def lint_document(*, store, doc_type: str, fields: dict) -> dict:
    schema = _load_schema(doc_type)
    errors: list[dict] = []
    for name, tname in schema.get("required", {}).items():
        if name not in fields:
            errors.append({"field": name, "problem": "missing"})
        elif not isinstance(fields[name], _TYPES.get(tname, str)):
            errors.append({"field": name, "problem": f"type:{tname}"})
    for name, tname in schema.get("optional", {}).items():
        if name in fields and not isinstance(fields[name], _TYPES.get(tname, str)):
            errors.append({"field": name, "problem": f"type:{tname}"})
    return {"doc_type": doc_type, "errors": errors, "error_count": len(errors),
            "ok": not errors}

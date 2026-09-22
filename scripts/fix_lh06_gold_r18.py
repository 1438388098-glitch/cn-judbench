"""R18：lh-06（继承纠纷，as_of=2020-06-01）金样时效病修正。

全库锚点时效扫描（见 docs/calc-real-model-report.md §C5）发现：lh-06 的
law_anchors/gold.citations 挂民法典509——该条在 as_of=2020-06-01 尚未生效
（民法典 2021-01-01 施行），且 509（合同编全面履行）与继承纠纷争点不对口。
mock:gold 回灌 lh-06 得 0（金样无法自证）。

修正为当时有效规范：继承法第十条（法定继承顺序，1985-10-01 施行，
2021-01-01 随民法典施行废止）。配套 lawkb 增补见 add_lawkb_laws_r16.py。

用法::

    python scripts/fix_lh06_gold_r18.py
"""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data" / "public" / "long_horizon_case.jsonl"

SUC = "中华人民共和国继承法"


def main() -> int:
    items = [json.loads(l) for l in PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    hit = 0
    for it in items:
        if it["id"] != "lh-06":
            continue
        it["law_anchors"] = [{"law": SUC, "article": "10", "effective_on": "1985-10-01"}]
        it["gold"]["citations"] = [{"law": SUC, "article": "10"}]
        hit += 1
    PATH.write_text(
        "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items),
        encoding="utf-8",
    )
    print(f"patched {hit} item -> {PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

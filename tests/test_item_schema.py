"""题面 Item 模型校验：枚举闭合、composite 规则、split×contamination 一致性。"""

import pytest
from pydantic import ValidationError

from cnjudbench.schemas.item import Item


def base_item(**overrides) -> dict:
    d = {
        "id": "t-001",
        "task_id": "s_charge_subsume",
        "capability": "S",
        "difficulty": 3,
        "interaction": "L1",
        "roles": ["judge"],
        "domain": "criminal",
        "output_type": "structured",
        "hcut": ["Cit"],
        "instruction": "判断罪名",
        "input": "案情……",
        "gold": {"charge": "盗窃罪"},
        "law_anchors": [{"law": "中华人民共和国刑法", "article": "264"}],
        "as_of": "2024-06-01",
        "canary": "CNJB-CANARY-9f3a",
        "split": "public",
        "contamination_risk": "low",
        "source": "real_amended",
    }
    d.update(overrides)
    return d


def test_valid_item_passes():
    item = Item.model_validate(base_item())
    assert item.id == "t-001"
    assert item.law_anchors[0].law == "中华人民共和国刑法"


def test_composite_requires_components():
    with pytest.raises(ValidationError, match="components"):
        Item.model_validate(base_item(output_type="composite"))
    ok = Item.model_validate(
        base_item(output_type="composite", components=["extract", "gen"])
    )
    assert ok.components == ["extract", "gen"]
    with pytest.raises(ValidationError, match="components"):
        Item.model_validate(base_item(output_type="composite", components=["gen", "composite"]))


def test_non_composite_cannot_have_components():
    with pytest.raises(ValidationError, match="composite"):
        Item.model_validate(base_item(components=["gen"]))


def test_output_type_enum_closed():
    with pytest.raises(ValidationError):
        Item.model_validate(base_item(output_type="mixed"))  # 历史错误值，已废除
    with pytest.raises(ValidationError):
        Item.model_validate(base_item(output_type="extract+gen"))


def test_holdout_must_be_low_contamination():
    with pytest.raises(ValidationError, match="holdout"):
        Item.model_validate(base_item(split="holdout", contamination_risk="high"))
    Item.model_validate(base_item(split="public", contamination_risk="high"))  # public 可 high


@pytest.mark.parametrize(
    "field,value",
    [
        ("hcut", ["cit"]),  # 大小写敏感
        ("hcut", []),
        ("interaction", "L5"),
        ("domain", "maritime"),
        ("difficulty", 5),
        ("canary", "CANARY-9f3a"),
        ("capability", "X"),
    ],
)
def test_bad_enums_rejected(field, value):
    with pytest.raises(ValidationError):
        Item.model_validate(base_item(**{field: value}))


def test_composite_capability_ok():
    Item.model_validate(base_item(capability="C/G"))
    Item.model_validate(base_item(capability="Cit"))

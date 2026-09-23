# -*- coding: utf-8 -*-
"""c014（R6）：providers.apply_profile_to_args——profile 填充语义回归。

约束：只填用户未显式指定的项（显式优先）；模型规格统一为 openai:<id>
复用适配器；mock:* 永不改写；_cnjb_* 侧信道恒写入（账本/判分依赖）。
"""
from argparse import Namespace

from cnjudbench.providers import apply_profile_to_args


def _profile(**over):
    base = {"provider": "zhipu", "label": "智谱", "model": "glm-5.3-flash",
            "model_ref": "zhipu:glm-5.3-flash", "base_url": "https://api.example/v4",
            "price_key": "glm53", "timeout": 90.0, "temperature": 0.2,
            "reasoning_effort": "high", "thinking": {"type": "enabled"}, "api_key": "k",
            "note": None}
    base.update(over)
    return base


def test_fills_missing_fields_only():
    args = Namespace(model="zhipu:glm-5.3-flash")
    apply_profile_to_args(args, _profile())
    assert args.base_url == "https://api.example/v4"
    assert args.timeout == 90.0
    assert args.reasoning_effort == "high"
    assert args.model == "openai:glm-5.3-flash"


def test_explicit_values_win():
    args = Namespace(model="openai:glm-5.3-flash", base_url="https://mine/v1",
                     timeout=5.0, reasoning_effort="low")
    apply_profile_to_args(args, _profile())
    assert args.base_url == "https://mine/v1"   # 用户显式指定不被覆盖
    assert args.timeout == 5.0
    assert args.reasoning_effort == "low"
    assert args.model == "openai:glm-5.3-flash"  # openai: 前缀保持


def test_mock_model_never_rewritten():
    args = Namespace(model="mock:gold")
    apply_profile_to_args(args, _profile())
    assert args.model == "mock:gold"


def test_sidechannel_attrs_always_set():
    args = Namespace(model="zhipu:glm-5.3-flash")
    apply_profile_to_args(args, _profile(price_key="glm53", thinking=None))
    assert args._cnjb_profile["price_key"] == "glm53"
    assert args._cnjb_thinking is None
    assert args._cnjb_price_key == "glm53"

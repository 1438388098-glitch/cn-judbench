# -*- coding: utf-8 -*-
"""c393：providers 配置层裸函数单测（此前仅被 CLI 子进程冒烟间接触达）。

覆盖：load_env_local 解析语义 / parse_model_ref 路由 / resolve_profile 合并与
报错路径 / apply_profile_to_args「仅当用户未显式指定」契约。全部 tmp 注入，
不读真实 .env.local、不触网络。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from cnjudbench import providers as P

# autouse 夹具会 patch P.load_env_local——模块导入时保存原始实现供其自测
_REAL_LOAD_ENV = P.load_env_local


@pytest.fixture()
def provs():
    return {
        "zeta": {
            "label": "Zeta",
            "base_url": "https://api.zeta.example/v1",
            "api_key_env": ["ZETA_API_KEY"],
            "defaults": {"temperature": 0.3, "timeout": 90,
                         "thinking": {"type": "enabled"}},
            "models": {
                "m-1": {"price_key": "m1", "reasoning_effort": "high"},
                "m-2": {},
            },
        },
    }


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    monkeypatch.delenv("ZETA_API_KEY", raising=False)
    monkeypatch.setattr(P, "load_env_local", lambda path=None: {})


def test_load_env_local_parses_and_strips(tmp_path):
    f = tmp_path / ".env.local"
    f.write_text('# 注释\nA=1\nB = "two words" \nC=\'x\'\n非法行\n\n', encoding="utf-8")
    assert _REAL_LOAD_ENV(f) == {"A": "1", "B": "two words", "C": "x"}


def test_load_env_local_missing_file_empty(tmp_path):
    assert _REAL_LOAD_ENV(tmp_path / "nope") == {}


def test_parse_model_ref_routes_by_provider_table(provs):
    assert P.parse_model_ref("zeta:m-1", provs) == ("zeta", "m-1")
    assert P.parse_model_ref("openai:x", provs) == (None, "x")
    assert P.parse_model_ref("mock:gold", provs) == (None, "mock:gold")  # mock 永不路由
    assert P.parse_model_ref("bare-model", provs) == (None, "bare-model")
    assert P.parse_model_ref("unknown:x", provs) == (None, "unknown:x")


def test_resolve_profile_merges_defaults_and_model(provs):
    prof = P.resolve_profile("zeta:m-1", providers=provs)
    assert prof["provider"] == "zeta" and prof["model"] == "m-1"
    assert prof["price_key"] == "m1"
    assert prof["timeout"] == 90.0 and prof["temperature"] == 0.3  # 回落 provider defaults
    assert prof["reasoning_effort"] == "high"  # 模型级覆盖 defaults
    assert prof["thinking"] == {"type": "enabled"}
    assert prof["api_key"] is None  # 无键如实 None，禁编造


def test_resolve_profile_bare_model_found_via_models_table(provs):
    prof = P.resolve_profile("m-2", providers=provs)
    assert prof["provider"] == "zeta" and prof["model"] == "m-2"


def test_resolve_profile_unknown_provider_and_model(provs):
    with pytest.raises(SystemExit, match="未知提供商"):
        P.resolve_profile("ghost:m-1", providers=provs)
    with pytest.raises(SystemExit, match="无模型"):
        P.resolve_profile("zeta:m-9", providers=provs)


def test_apply_profile_to_args_only_fills_unspecified(provs):
    prof = P.resolve_profile("zeta:m-1", providers=provs)

    args = SimpleNamespace(model="zeta:m-1", base_url=None, timeout=60.0,
                           reasoning_effort=None)
    P.apply_profile_to_args(args, prof)
    assert args.base_url == "https://api.zeta.example/v1"
    assert args.timeout == 90.0
    assert args.model == "openai:m-1"  # 统一 openai: 以复用适配器
    assert args._cnjb_price_key == "m1"

    args2 = SimpleNamespace(model="openai:m-1", base_url="https://custom",
                            timeout=5.0, reasoning_effort="low")
    P.apply_profile_to_args(args2, prof)
    assert args2.base_url == "https://custom"  # 用户显式值不被覆盖
    assert args2.timeout == 5.0
    assert args2.reasoning_effort == "low"

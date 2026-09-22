"""提供商配置解析：base_url / 密钥环境变量 / 默认采样与思考参数 / 价目键。

密钥**只**从环境变量或仓库根 `.env.local`（已 gitignore）读取，不进库、不进日志。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
PROVIDERS_PATH = ROOT / "configs" / "providers.yaml"
ENV_LOCAL = ROOT / ".env.local"


def load_providers(path: Path | None = None) -> dict[str, Any]:
    p = path or PROVIDERS_PATH
    data = yaml.safe_load(p.read_text(encoding="utf-8-sig")) or {}
    return data


def load_env_local(path: Path | None = None) -> dict[str, str]:
    """解析 `.env.local`（KEY=VALUE，# 注释）。不写回、不打印值。"""
    p = path or ENV_LOCAL
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def resolve_api_key(provider: dict, env_local: dict[str, str] | None = None) -> str | None:
    """取键顺序：进程环境变量优先，其次 `.env.local`（标准 dotenv 语义：
    显式导出的环境变量比落盘文件更具体，防止 .env.local 旧键遮蔽会话新键）。"""
    env_local = env_local if env_local is not None else load_env_local()
    for name in provider.get("api_key_env") or []:
        if os.environ.get(name):
            return os.environ[name]
        if env_local.get(name):
            return env_local[name]
    return None


def parse_model_ref(ref: str, providers: dict[str, Any] | None = None) -> tuple[str | None, str]:
    """``zhipu:glm-5.3-flash`` → (zhipu, glm-5.3-flash)；``openai:x`` → (None, x)。"""
    if ":" in ref and not ref.startswith("mock:"):
        prov, _, model = ref.partition(":")
        if prov in (providers or {}):
            return prov, model
        if prov == "openai":
            return None, model
    return None, ref


def resolve_profile(
    model_ref: str,
    *,
    provider_name: str | None = None,
    providers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """合并提供商默认值与模型条目 → 适配器/CLI 可用配置。

    返回键：provider, model, base_url, price_key, timeout, temperature,
    reasoning_effort, thinking, api_key, label。
    """
    providers = providers if providers is not None else load_providers()
    auto_prov, model = parse_model_ref(model_ref, providers)
    pname = provider_name or auto_prov
    if not pname:
        # 裸模型名：在各提供商 models 里找
        for name, cfg in providers.items():
            if model in (cfg.get("models") or {}):
                pname = name
                break
    if not pname or pname not in providers:
        raise SystemExit(
            f"未知提供商/模型: {model_ref!r}；可用: "
            + ", ".join(f"{p}:{m}" for p, c in providers.items() for m in (c.get("models") or {}))
        )
    pcfg = providers[pname]
    defaults = dict(pcfg.get("defaults") or {})
    mentries = pcfg.get("models") or {}
    if model not in mentries:
        raise SystemExit(
            f"提供商 {pname} 无模型 {model!r}；可选: {', '.join(mentries) or '(无)'}"
        )
    ment = dict(mentries[model] or {})
    thinking = ment.get("thinking", defaults.get("thinking"))
    effort = ment.get("reasoning_effort", defaults.get("reasoning_effort"))
    # 用户显式传入的 effort 由 CLI 覆盖（此处只给默认）
    api_key = resolve_api_key(pcfg)
    return {
        "provider": pname,
        "label": pcfg.get("label", pname),
        "model": model,
        "model_ref": f"{pname}:{model}",
        "base_url": pcfg.get("base_url"),
        "price_key": ment.get("price_key"),
        "timeout": float(ment.get("timeout", defaults.get("timeout", 60))),
        "temperature": float(ment.get("temperature", defaults.get("temperature", 0.0))),
        "reasoning_effort": effort,
        "thinking": thinking,
        "api_key": api_key,
        "note": ment.get("note"),
    }


def apply_profile_to_args(args, profile: dict[str, Any]) -> None:
    """把 profile 填进 argparse.Namespace（仅当用户未显式指定）。"""
    if not getattr(args, "base_url", None):
        args.base_url = profile["base_url"]
    if getattr(args, "timeout", 60.0) in (60.0, None) and profile.get("timeout"):
        args.timeout = profile["timeout"]
    if not getattr(args, "reasoning_effort", None) and profile.get("reasoning_effort"):
        args.reasoning_effort = profile["reasoning_effort"]
    # 模型规格统一为 openai:<id> 以复用适配器
    raw = getattr(args, "model", "")
    if raw and not raw.startswith("mock:") and not raw.startswith("openai:"):
        args.model = f"openai:{profile['model']}"
    elif raw.startswith("openai:"):
        pass
    args._cnjb_profile = profile  # 供账本 price_key 使用
    args._cnjb_thinking = profile.get("thinking")
    args._cnjb_price_key = profile.get("price_key")

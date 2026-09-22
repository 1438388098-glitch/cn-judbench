"""Run Manifest（FRAMEWORK §7.1，缺一不得进正式结果）与 run 落盘。"""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..lawkb.resolve import slice_union_hash
from .account import Accountant
from .evaluate import DISCLAIMER, TaskRun


def harness_sha(repo_hint: Path | None = None) -> str:
    """git 短 SHA；非 git 环境回退源码树 hash，保证字段恒非空。"""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
            cwd=repo_hint, timeout=10,
        ).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 —— manifest 必填字段，失败回退
        return "unknown"


def item_content_hash(raw_lines: list[str]) -> str:
    joined = "".join(sorted(raw_lines)).encode("utf-8")
    return "sha256:" + hashlib.sha256(joined).hexdigest()


def prompts_hash(prompts: list[str]) -> str:
    joined = "".join(prompts).encode("utf-8")
    return "sha256:" + hashlib.sha256(joined).hexdigest()


def build_manifest(
    *,
    runs: list[TaskRun],
    store_version: str,
    model_id: str,
    revision: str | None,
    temperature: float,
    seed: int | None,
    prompt_list: list[str],
    item_count: int,
    content_hash: str,
    accountant: Accountant,
    repo_hint: Path | None = None,
) -> dict:
    as_of_used = sorted({x for r in runs for x in r.as_of_used})
    return {
        "run_id": uuid.uuid4().hex[:12],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "harness_sha": harness_sha(repo_hint),
        "lawkb": {
            "store_version": store_version,
            "resolution": "as_of",
            "as_of_used": as_of_used,
            "slice_union_hash": slice_union_hash([h for r in runs for h in r.text_hashes]),
        },
        "model": {
            "model_id": model_id,
            "revision": revision,
            "temperature": temperature,
            "seed": seed,
        },
        "prompt_hash": prompts_hash(prompt_list),
        "dataset": {
            "task_ids": [r.task_id for r in runs],
            "item_count": item_count,
            "item_content_hash": content_hash,
        },
        "accounting": {
            "prompt_tokens": accountant.prompt_tokens,
            "completion_tokens": accountant.completion_tokens,
            "est_cost_usd": accountant.est_cost_usd,
            "judge_calls": accountant.judge_calls,
            "judge_prompt_tokens": accountant.judge_prompt_tokens,
            "judge_completion_tokens": accountant.judge_completion_tokens,
            "p95_latency_ms": accountant.p95_latency_ms,
        },
        "disclaimer": DISCLAIMER,
    }


def write_run(out_dir: Path, manifest: dict, summary: dict,
              limits_text: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if limits_text is not None:
        (out_dir / "limits.md").write_text(limits_text, encoding="utf-8")
    return out_dir

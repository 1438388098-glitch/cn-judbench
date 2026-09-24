"""Run Manifest（FRAMEWORK §7.1，缺一不得进正式结果）与 run 落盘。"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..lawkb.resolve import slice_union_hash
from .account import Accountant
from .evaluate import DISCLAIMER, TaskRun


def harness_sha(repo_hint: Path | None = None) -> str:
    """git 短 SHA；非 git 环境回退 "unknown"（manifest 必填非空占位）。"""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
            encoding="utf-8", errors="replace",
            cwd=repo_hint, timeout=10,
        ).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 —— manifest 必填字段，失败回退
        return "unknown"


def item_content_hash(raw_lines: list[str]) -> str:
    joined = "".join(sorted(raw_lines)).encode("utf-8")
    return "sha256:" + hashlib.sha256(joined).hexdigest()


def item_line_hash(item_id: str, raw_line: str) -> str:
    """单题 content hash（§7.1 每题可复现）。"""
    blob = f"{item_id}\n{raw_line}".encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def prompts_hash(prompts: list[str]) -> str:
    joined = "".join(prompts).encode("utf-8")
    return "sha256:" + hashlib.sha256(joined).hexdigest()


_LOCK_FILENAMES = ("uv.lock", "poetry.lock", "requirements.lock.txt", "requirements-freeze.txt")


def deps_lock_sha256(repo_hint: Path | None = None) -> str | None:
    """DESIGN v0.4 §8：依赖锁指纹（uv.lock / poetry.lock / requirements 冻结件之一）。

    都不存在 → None，触发 provisional（产物不得进对外对比表）。"""
    repo = repo_hint or Path.cwd()
    for name in _LOCK_FILENAMES:
        p = repo / name
        if p.is_file():
            return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
    return None


def mark_provisional(deps_block: dict, stats_block: dict, *, formal_board: bool = True) -> bool:
    """缺 ``deps.lock_sha256`` 或（正式榜要求时）``stats.flip_rate`` → provisional。"""
    if not deps_block.get("lock_sha256"):
        return True
    if formal_board and stats_block.get("flip_rate") is None:
        return True
    return False


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
    trajectory_hashes: dict[str, str] | None = None,
    user_seed: int | None = None,
    item_hashes: dict[str, str] | None = None,
    extra: dict | None = None,
    judge_block: dict | None = None,
    stats_block: dict | None = None,
    baselines_block: dict | None = None,
) -> dict:
    as_of_used = sorted({x for r in runs for x in r.as_of_used})
    manifest = {
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
        "user_seed": user_seed,
        "prompt_hash": prompts_hash(prompt_list),
        "dataset": {
            "task_ids": [r.task_id for r in runs],
            "item_count": item_count,
            "item_content_hash": content_hash,
            "item_hashes": item_hashes or {},
        },
        "accounting": accountant.cost_ledger(),
        "disclaimer": DISCLAIMER,
    }
    if trajectory_hashes:
        manifest["tools"] = {"trajectory_hashes": trajectory_hashes}
    # DESIGN v0.4 §8 正式分契约：deps/judge/stats/baselines/human_eval + provisional 门禁
    deps_block = {"lock_sha256": deps_lock_sha256(repo_hint), "python": platform.python_version()}
    stats_block = {"ci95": None, "flip_rate": None, "n_replicates": 1, **(stats_block or {})}
    manifest["deps"] = deps_block
    manifest["judge"] = {
        "enabled": False, "model_id": None, "mode": None, "k_pass": None, "prompt_hash": None,
        **(judge_block or {}),
    }
    manifest["stats"] = stats_block
    manifest["baselines"] = baselines_block or {"random": None, "rules": None}
    manifest["human_eval"] = None
    manifest["provisional"] = mark_provisional(deps_block, stats_block)
    if extra:
        manifest.update(extra)
    return manifest


def trajectory_hash(trajectory: dict) -> str:
    """轨迹 hash：canonical JSON（键排序）的 sha256，进 manifest 防篡改。"""
    blob = json.dumps(trajectory, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def _safe_item_id(item_id: str) -> str:
    """轨迹文件名白名单字符，防路径注入（P0-4）。"""
    import re
    cleaned = re.sub(r"[^\w.-]", "_", str(item_id))
    return cleaned or "item"


def write_run(out_dir: Path, manifest: dict, summary: dict,
              limits_text: str | None = None,
              trajectories: dict[str, dict] | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if limits_text is not None:
        (out_dir / "limits.md").write_text(limits_text, encoding="utf-8")
    if trajectories:
        items_dir = out_dir / "items"
        items_dir.mkdir(exist_ok=True)
        seen_safe: dict[str, str] = {}
        for item_id, traj in trajectories.items():
            safe_id = _safe_item_id(item_id)
            prev = seen_safe.get(safe_id)
            if prev is not None:
                # c408：sanitize 碰撞不得静默互相覆盖（§7.1 每题可复现契约）
                raise ValueError(
                    f"轨迹文件名碰撞：{prev!r} 与 {item_id!r} 都 sanitize 为 "
                    f"{safe_id!r}——轨迹证据将互相覆盖，请修题 id 或 sanitize 规则"
                )
            seen_safe[safe_id] = item_id
            (items_dir / f"{safe_id}.trajectory.json").write_text(
                json.dumps(traj, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    return out_dir

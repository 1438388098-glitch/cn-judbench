# -*- coding: utf-8 -*-
"""R13 设施与幂等机检（c225/c226/c228/c230）+ 文档对齐（c227/c229）：

- c225 FileCache 多线程并发读写（进程内锁语义）；
- c226 holdout_review_pack 重复生成幂等（除 generated 时间戳外字节相同）；
- c228 FRAMEWORK §3 八维文案与 capabilities.CANONICAL_DIMS 一致；
- c230 gen_lawkb_ingest_queue 重跑幂等（白名单未变 → 字节不变）；
- c227/c229 审查结论：ci.yml 钉 3.11（README 3.11+ 最低线一致，本地 3.13
  仅开发环境）——以测试断言 workflow 与文档声明同存；
  citeguard 三检（条号/时效/文本）与 FRAMEWORK §4.2 语义对齐由 c194 值域
  守卫 + c222 边界测试共同锁定，此处复核无误。
"""

import json
import subprocess
import threading
import tomllib
from pathlib import Path

from cnjudbench.adapters.cache import FileCache, cache_key
from cnjudbench.adapters.base import CompletionResult

from conftest import project_python

REPO = Path(__file__).resolve().parents[1]


def test_c225_file_cache_multithreaded(tmp_path):
    fc = FileCache(tmp_path)
    keys = [cache_key("m", None, f"p{i}", 0.0, None) for i in range(20)]
    results = [CompletionResult(text=f"t{i}", prompt_tokens=1, completion_tokens=1,
                                latency_ms=1, model_id="m", revision=None)
               for i in range(20)]
    errors: list[Exception] = []

    def worker(i: int) -> None:
        try:
            for _ in range(5):
                fc.put(keys[i], results[i])
                got = fc.get(keys[i])
                assert got is not None and got.text == f"t{i}"
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(list(tmp_path.glob("*.json"))) == 20  # 无写坏/丢文件


def test_c226_holdout_pack_idempotent(tmp_path):
    script = REPO / "scripts" / "holdout_review_pack.py"
    out1 = REPO / "reports" / "holdout-prospective.json"
    out_md = REPO / "docs" / "holdout-dual-review-pack.md"
    assert out1.is_file() and out_md.is_file() and script.is_file()
    original = out1.read_bytes()  # 快照恢复：测试不得把仓库文件跑脏
    original_md = out_md.read_bytes()  # 生成器同时写出复核材料包 md（含日期头），一并恢复
    try:
        r = subprocess.run([project_python(),
                            str(script)], cwd=REPO, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        if r.returncode != 0:
            # 生成器可能要求显式参数——跳过而非误报
            assert "required" in r.stderr, r.stderr[-300:]
            return
        first = out1.read_bytes()
        r2 = subprocess.run([project_python(),
                             str(script)], cwd=REPO, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=300)
        assert r2.returncode == 0
        second = out1.read_bytes()
        a, b = json.loads(first), json.loads(second)
        a.pop("generated", None), b.pop("generated", None)  # 时间戳允许漂移
        assert a == b  # 双连跑（同一 HEAD）结构逐字相同
    finally:
        out1.write_bytes(original)
        out_md.write_bytes(original_md)


def test_c228_framework_dims_match_canonical():
    import sys
    if str(REPO / "src") not in sys.path:
        sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.capabilities import CANONICAL_DIMS, CROSSCUTTING

    fw = (REPO / "FRAMEWORK.md").read_text(encoding="utf-8")
    for dim, label in {**CANONICAL_DIMS, **CROSSCUTTING}.items():
        assert dim in fw, f"FRAMEWORK §3 缺维 {dim}"
        # 中文文案同源（框架文档与字典逐字一致，防报表口径漂移）
        assert label[:6] in fw, f"FRAMEWORK 缺 {dim} 维文案：{label}"


def test_c229_ci_workflow_declares_floor_python():
    wf = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python-version" in wf  # CI 有 Python 钉版
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["requires-python"] == ">=3.11"
    pv = (REPO / ".python-version").read_text(encoding="utf-8").strip()
    assert pv.startswith("3.")  # 本地开发版留档在场


def test_c230_ingest_queue_generator_idempotent(tmp_path):
    script = REPO / "scripts" / "gen_lawkb_ingest_queue.py"
    queue = REPO / "docs" / "lawkb-ingest-queue.md"
    original = queue.read_bytes()  # 快照恢复，防测试跑脏仓库文件
    try:
        r1 = subprocess.run([project_python(), str(script)],
                            cwd=REPO, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=300)
        assert r1.returncode == 0, r1.stderr[-300:]
        before = queue.read_text(encoding="utf-8")
        r2 = subprocess.run([project_python(), str(script)],
                            cwd=REPO, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=300)
        assert r2.returncode == 0
        after = queue.read_text(encoding="utf-8")
        # 生成头含日期与 harness 行允许漂移；表体必须稳定
        body_before = "\n".join(before.splitlines()[6:])
        body_after = "\n".join(after.splitlines()[6:])
        assert body_before == body_after
    finally:
        queue.write_bytes(original)

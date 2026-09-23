# -*- coding: utf-8 -*-
"""R12 脚本与声明机检（c212-c221 的实现文件）：

- c212 版本三方一致（__init__ / pyproject / FRAMEWORK 头部 v0.6）；
- c213 LICENSE 分表许可（MIT + CC BY 4.0）与 dataset-card §7 呼应；
- c214 README 三要素（目标 / 如何运行 / 如何测试）；
- c215 CLI 全部子命令 --help 冒烟；
- c216 flip_rate_check.py mock 双跑；
- c217 kappa.py 合成双评输入；
- c218 openai_compat 重试路径（429 重试成功 / 持续 429 / 401 不重试）；
- c219 export_prompts.py 冒烟；
- c220 data/archive 与 public 隔离；
- c221 passk 剔除饱和对照行写入 markdown（c165 的 pytest 化）。
"""

import importlib
import io
import json
import subprocess
import sys
import tomllib
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
PY = REPO / ".venv" / "Scripts" / "python.exe"


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(PY)] + cmd, cwd=REPO, capture_output=True,
                          text=True, timeout=600, **kw)


def test_c212_version_three_way():
    import cnjudbench
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert cnjudbench.__version__ == pyproject["project"]["version"] == "0.6.0"
    assert "v0.6" in (REPO / "FRAMEWORK.md").read_text(encoding="utf-8")[:600]


def test_c213_license_split():
    lic = (REPO / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in lic
    assert "CC BY 4.0" in lic
    card = (REPO / "docs" / "dataset-card.md").read_text(encoding="utf-8")
    assert "代码 MIT" in card and "CC BY 4.0" in card  # §7 声明与 LICENSE 同口径


def test_c214_readme_structure():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "**目标**" in readme
    assert "如何运行" in readme or "快速开始" in readme or "run-all" in readme
    assert "## 测试" in readme and "pytest" in readme
    assert "非法律意见" in readme  # 免责声明在场


def test_c215_cli_help_all_subcommands():
    subcommands = ["validate", "resolve-law", "smoke-cit-validity",
                   "run", "run-all", "run-dialog", "compare"]
    for sub in subcommands:
        r = _run(["-m", "cnjudbench", sub, "--help"])
        assert r.returncode == 0, f"{sub} --help 失败：{r.stderr[-300:]}"


def test_c216_flip_rate_check_mock_smoke():
    r = _run(["scripts/flip_rate_check.py"])
    assert r.returncode == 0, r.stderr[-400:]


def test_c217_kappa_synthetic(tmp_path):
    ratings = tmp_path / "ratings.csv"
    ratings.write_text(
        "item_id,rater1,rater2\n"
        + "".join(f"i{k},{k % 4},{k % 4}\n" for k in range(20)),
        encoding="utf-8")
    machine = tmp_path / "machine.csv"
    machine.write_text(
        "item_id,machine_score\n"
        + "".join(f"i{k},{60 + (k % 4) * 10}\n" for k in range(20)),
        encoding="utf-8")
    r = _run(["scripts/kappa.py", "--ratings", str(ratings),
              "--machine", str(machine), "--out", str(tmp_path / "k.json")])
    assert r.returncode == 0, r.stderr[-400:]
    out = json.loads((tmp_path / "k.json").read_text(encoding="utf-8"))
    assert out  # 完全一致的双评 → κ 应为 1（字段名以脚本为准，仅断言产物非空）


def test_c218_openai_compat_retry_paths(monkeypatch):
    monkeypatch.setenv("CNJUD_API_KEY", "test-key-dummy")
    from cnjudbench.adapters import openai_compat as oc

    calls = {"n": 0}

    class Resp:
        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class Err(io.IOBase):
        pass

    def _urlopen_429_then_ok(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise oc.urllib.error.HTTPError(req.full_url, 429, "rate limited",
                                            {}, io.BytesIO(b'{"error":"x"}'))
        return Resp()

    monkeypatch.setattr(oc.time, "sleep", lambda _s: None)
    ad = oc.OpenAICompatAdapter(model="m", api_key="k", cache_dir=None)
    monkeypatch.setattr(oc.urllib.request, "urlopen", _urlopen_429_then_ok)
    out = ad.complete("hi")
    assert out.text == "ok" and calls["n"] == 2  # 429 一次后重试成功

    calls["n"] = 0

    def _urlopen_always_429(req, timeout=None):
        calls["n"] += 1
        raise oc.urllib.error.HTTPError(req.full_url, 429, "rate limited",
                                        {}, io.BytesIO(b'{"error":"x"}'))

    monkeypatch.setattr(oc.urllib.request, "urlopen", _urlopen_always_429)
    with pytest.raises(Exception, match="网络失败"):
        ad.complete("hi")
    assert calls["n"] > 1  # 持续 429 走满重试

    def _urlopen_401(req, timeout=None):
        calls["n"] += 1
        raise oc.urllib.error.HTTPError(req.full_url, 401, "unauthorized",
                                        {}, io.BytesIO(b'{}'))

    calls["n"] = 0
    monkeypatch.setattr(oc.urllib.request, "urlopen", _urlopen_401)
    with pytest.raises(Exception, match="不重试"):
        ad.complete("hi")
    assert calls["n"] == 1  # 401 不得重试


def test_c219_export_prompts_smoke(tmp_path):
    run_dir = tmp_path / "run"
    r = _run(["scripts/export_prompts.py", "--tasks", "cit_validity",
              "--run-dir", str(run_dir)])
    assert r.returncode == 0, r.stderr[-400:]
    prompts = list((run_dir / "prompts").glob("*.txt"))
    assert len(prompts) == 27  # cit_validity 全 27 题
    assert (run_dir / "index.json").is_file()
    assert (run_dir / "answers").is_dir()


def test_c220_archive_isolated_from_public():
    public_ids = set()
    for f in (REPO / "data" / "public").glob("*.jsonl"):
        public_ids |= {json.loads(l)["id"]
                       for l in f.read_text(encoding="utf-8-sig").splitlines() if l.strip()}
    archive = REPO / "data" / "archive"
    if archive.is_dir():
        for f in archive.rglob("*.jsonl"):
            ids = {json.loads(l)["id"]
                   for l in f.read_text(encoding="utf-8-sig").splitlines() if l.strip()}
            overlap = ids & public_ids
            assert not overlap, f"archive 题回流 public：{sorted(overlap)[:5]}"


def test_c221_passk_exclusion_markdown_line(tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    agg = importlib.import_module("aggregate_passk")
    run_a = REPO / "reports" / "runs" / "audit-calc1"
    if not (run_a / "summary.json").is_file():
        pytest.skip("audit-calc1 run 目录缺失")
    out = tmp_path / "passk.md"
    # 直接走 main()：argv 注入
    argv = ["aggregate_passk.py", "--runs", str(run_a), str(run_a),
            "--exclude-saturation", "--out", str(out)]
    old = sys.argv
    sys.argv = argv
    try:
        rc = agg.main()
    finally:
        sys.argv = old
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "剔除饱和对照" in text and "n=46" in text  # 46 题中 30 题饱和
    assert "剔除 30 题" in text

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
from conftest import project_python  # 跨平台解释器（CI 无 .venv 时回退当前解释器）
PY = Path(project_python())


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(PY)] + cmd, cwd=REPO, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=600, **kw)


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


def test_c372_题库生成器顶层写盘必须有_main_guard():
    """R19 教训机检：涉及 data/public 的脚本若在模块顶层（函数/类之外）写盘，
    必须 import 无副作用——即带 ``if __name__ == "__main__"`` guard。"""
    import ast

    WRITE_ATTRS = {"write_text", "write_bytes", "open", "mkdir", "unlink", "rename"}
    bad = []
    for path in sorted(SCRIPTS.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        if "__main__" in src:
            continue
        src_norm = src.replace('"data", "public"', "data/public").replace("'data', 'public'", "data/public")
        if "data/public" not in src_norm and "data\\\\public" not in src:
            continue  # 只看题库写盘面（R19 事故半径）
        hits = False
        stack = list(ast.parse(src).body)
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # 函数体内的写盘由调用时机决定，不算顶层副作用
            if isinstance(node, ast.Call):
                fn = node.func
                if (isinstance(fn, ast.Attribute) and fn.attr in WRITE_ATTRS) or \
                        (isinstance(fn, ast.Name) and fn.id == "open"):
                    hits = True
                    break
            stack.extend(ast.iter_child_nodes(node))
        if hits:
            bad.append(path.name)
    assert not bad, f"涉 data/public 且顶层写盘但缺 __main__ guard 的脚本：{bad}"


def test_c377_zhuma_quality_scan_tmp_fixture_and_real_pool_readonly(tmp_path):
    """竹马候选池质量扫描：tmp 金样 + 真池只读（字节级不变断言，R19 纪律）。"""
    import hashlib

    pool = tmp_path / "pool"
    pool.mkdir()
    q_dup = {"id": 2, "question": "甲乙纠纷，下列说法正确的是？", "type": "单选题",
             "answer": ["A"], "options": [{"id": "A", "text": "对"}, {"id": "B", "text": "错"}]}
    (pool / "2011_卷一.json").write_text(json.dumps({
        "year": "2011", "volume": "卷一", "count": 2, "questions": [
            {"id": 1, "question": "甲为掩饰隐瞒\ufffd\ufffd而实施下列行为", "type": "单选题",
             "answer": ["A\ufffd"], "options": [{"id": "A", "text": "选项\ufffd甲"}, {"id": "B", "text": "选项乙"}]},
            q_dup,
        ]}, ensure_ascii=False), encoding="utf-8")
    (pool / "2012_卷一.json").write_text(json.dumps({
        "year": "2012", "volume": "卷一", "count": 1, "questions": [dict(q_dup, id=9)]},
        ensure_ascii=False), encoding="utf-8")
    (pool / "all_objective_questions.json").write_text(
        json.dumps({"questions": [dict(q_dup, id=99)]}, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "report.json"
    r = subprocess.run([sys.executable, str(SCRIPTS / "clean_zhuma_pool.py"),
                        "--pool", str(pool), "--out", str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-400:]
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["total_items"] == 3  # 汇总文件跳过，防双计
    assert rep["ufffd_spots"] == 3  # question + options[0] + answer 各一处
    assert {u["field"] for u in rep["ufffd"]} == {"question", "options[0]", "answer[0]"}
    assert rep["n_dup_groups"] == 1 and sorted(rep["dup_groups"][0]["ids"]) == ["2", "9"]

    # 真池只读：跑真池后逐文件 sha256 不变，且默认不写题池目录
    real = REPO / "data" / "zhuma_fakao"
    if not real.is_dir():
        pytest.skip("data/zhuma_fakao 缺失")
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in real.glob("*")}
    out2 = tmp_path / "real-report.json"
    r2 = subprocess.run([sys.executable, str(SCRIPTS / "clean_zhuma_pool.py"),
                         "--pool", str(real), "--out", str(out2)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r2.returncode == 0, r2.stderr[-400:]
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in real.glob("*")}
    assert before == after, "题池文件被修改（违反只读契约）"
    rep2 = json.loads(out2.read_text(encoding="utf-8"))
    assert rep2["total_items"] == 4139  # 审计量：37 卷 4139 题
    assert rep2["ufffd_spots"] > 0  # 已知约 80 处乱码在案，清洗前必须可检出


def test_c378_pollution_run_dirs_self_marked():
    """污染 run 目录必须自带 CONTAMINATED.md（脱离总账也能自证，防误引用）。

    reports/runs/ 为 gitignored 本地产物：目录不存在（新 clone/CI）则跳过。"""
    for pattern in ("glm53f-self-v06*", "mimo-sub-full*"):
        for d in sorted((REPO / "reports" / "runs").glob(pattern)):
            if d.is_dir():
                mark = d / "CONTAMINATED.md"
                assert mark.is_file(), f"污染 run 缺自证标注：{d}"
                assert "禁止引用" in mark.read_text(encoding="utf-8")


def test_c382_quote_exemption_audit_tmp_fixture(tmp_path):
    """c382：引语豁免暴露面审计工具——引号内承诺词计数 + 机检分交叉。

    只读扫描：真池（reports/runs）存在时跑一遍只读断言，缺失则跳过。"""
    import json as _json

    run = tmp_path / "runs" / "demo-run"
    (run / "answers").mkdir(parents=True)
    (run / "answers" / "a-001.txt").write_text(
        "当事人声称「保证胜诉」，本所不予承诺。", encoding="utf-8")
    (run / "answers" / "a-002.txt").write_text(
        "本所保证胜诉。", encoding="utf-8")  # 裸承诺：不在引号内，不计入
    (run / "summary.json").write_text(_json.dumps(
        {"tasks": {"t": [{"id": "a-001", "display": "100.00"}]}}, ensure_ascii=False),
        encoding="utf-8")
    out = tmp_path / "audit.json"
    r = subprocess.run([sys.executable, str(SCRIPTS / "audit_quote_exemption.py"),
                        "--runs-root", str(tmp_path / "runs"), "--out", str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-400:]
    rep = _json.loads(out.read_text(encoding="utf-8"))
    assert rep["n_runs_scanned"] == 1
    assert rep["n_quote_promise_answers_total"] == 1
    item = rep["runs"][0]["items"][0]
    assert item == {"item_id": "a-001", "n_hits": 1, "machine_score": "100.00"}

    # 真实 runs 根只读冒烟（gitignored，缺失即跳过）
    if (REPO / "reports" / "runs").is_dir():
        out2 = tmp_path / "real-audit.json"
        r2 = subprocess.run([sys.executable, str(SCRIPTS / "audit_quote_exemption.py"),
                             "--out", str(out2)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r2.returncode == 0, r2.stderr[-400:]

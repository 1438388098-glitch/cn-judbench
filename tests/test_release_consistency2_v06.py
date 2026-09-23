# -*- coding: utf-8 -*-
"""R11 发布面一致性机检（c205/c206/c209）：

- c205 predicates_ref 全库可解析：复刻 runner 解析语义（task_dir 相对 →
  同名 basename，且不得越出任务包目录），把运行期 PredicateError 提前到测试期；
- c206 预注册六包名一致：FRAMEWORK/README 文档中的 CORE_SIX 任务名与
  metrics.compare.CORE_SIX_TASKS 及 tasks/ 目录三方对齐；
- c209 requirements-freeze 与 pyproject 依赖对账（freeze 是 provisional
  门禁的 deps 锁，与声明依赖脱节即失效）。
"""

import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_c205_predicates_ref_resolvable_for_all_items():
    import json

    for f in sorted((REPO / "data" / "public").glob("*.jsonl")):
        task_dir = REPO / "tasks" / f.stem
        assert task_dir.is_dir(), f"任务包目录缺失：{task_dir}"
        for ln in f.read_text(encoding="utf-8-sig").splitlines():
            if not ln.strip():
                continue
            item = json.loads(ln)
            ref = item.get("predicates_ref")
            if not ref:
                continue
            ref_path = Path(ref)
            assert not ref_path.is_absolute() and ".." not in ref_path.parts, \
                f"{item['id']}: predicates_ref 禁止绝对路径/..：{ref}"
            hits = [(task_dir / ref_path).is_file(),
                    (task_dir / ref_path.name).is_file()]
            assert any(hits), f"{item['id']}: predicates_ref 不可解析：{ref}"


def test_c206_core_six_names_align_docs_and_dirs():
    import sys
    if str(REPO / "src") not in sys.path:
        sys.path.insert(0, str(REPO / "src"))
    from cnjudbench.metrics.compare import CORE_SIX_TASKS

    assert len(CORE_SIX_TASKS) == 6
    fw = (REPO / "FRAMEWORK.md").read_text(encoding="utf-8")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for t in CORE_SIX_TASKS:
        assert (REPO / "tasks" / t).is_dir(), f"tasks/ 缺目录：{t}"
        assert t in fw, f"FRAMEWORK 未列预注册六包任务名：{t}"
        assert t in readme, f"README 未列预注册六包任务名：{t}"


def test_c209_freeze_covers_pyproject_deps():
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    deps = pyproject["project"]["dependencies"]
    freeze = (REPO / "requirements-freeze.txt").read_text(encoding="utf-8")
    frozen = {m.group(1).lower() for m in re.finditer(r"^([A-Za-z0-9_.-]+)==", freeze, re.M)}
    for dep in deps:
        name = re.split(r"[<>=!\[]", dep.strip())[0].strip().lower()
        name = name.replace("_", "-")
        assert name in frozen or f"{name.replace('-', '_')}" in frozen, \
            f"pyproject 依赖 {name} 不在 requirements-freeze.txt——请重新 pip freeze 提交"

"""providers.resolve_api_key 的取键优先级回归：进程环境 > .env.local。

背景（2026-09-22 DS 复跑 401）：.env.local 的 CNJUD_API_KEY（智谱键）遮蔽了
shell 显式导出的 DEEPSEEK_API_KEY。标准 dotenv 语义是环境变量优先。
"""

from cnjudbench.providers import resolve_api_key


def _prov(names):
    return {"api_key_env": names}


def test_process_env_beats_env_local(monkeypatch):
    monkeypatch.setenv("TEST_KEY_A", "from-env")
    got = resolve_api_key(_prov(["TEST_KEY_A"]),
                          env_local={"TEST_KEY_A": "from-file"})
    assert got == "from-env"


def test_env_local_used_when_no_process_env(monkeypatch):
    monkeypatch.delenv("TEST_KEY_B", raising=False)
    got = resolve_api_key(_prov(["TEST_KEY_B"]),
                          env_local={"TEST_KEY_B": "from-file"})
    assert got == "from-file"


def test_name_order_respected_across_sources(monkeypatch):
    """api_key_env 列表序仍生效：第一个名字只在文件里有 → 用文件；
    第一个名字彻底缺失 → 落到第二个名字（进程环境优先于文件）。"""
    monkeypatch.delenv("TEST_KEY_C", raising=False)
    monkeypatch.setenv("TEST_KEY_D", "from-env-d")
    got = resolve_api_key(_prov(["TEST_KEY_C", "TEST_KEY_D"]),
                          env_local={"TEST_KEY_C": "from-file-c",
                                     "TEST_KEY_D": "from-file-d"})
    assert got == "from-file-c"
    got2 = resolve_api_key(_prov(["TEST_KEY_C", "TEST_KEY_D"]),
                           env_local={"TEST_KEY_D": "from-file-d"})
    assert got2 == "from-env-d"


def test_missing_everywhere_returns_none(monkeypatch):
    monkeypatch.delenv("TEST_KEY_E", raising=False)
    assert resolve_api_key(_prov(["TEST_KEY_E"]), env_local={}) is None

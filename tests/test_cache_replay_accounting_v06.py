# -*- coding: utf-8 -*-
"""c243：FileCache 重放调用不污染 p95 延迟样本，且单独计数可审计。

背景：base.CompletionResult.cache_hit=True 时 latency/tokens 是旧值重放；
此前全部混进 _latencies，p95/均值被历史值污染且 manifest 无法看出重放量。
"""

from cnjudbench.runner.account import Accountant


def test_cache_replay_excluded_from_latency_and_counted():
    acc = Accountant()
    # 真实调用：延迟 100ms
    acc.add(10, 10, 100)
    # 两次重放：旧延迟值 9999ms 不得进入样本
    acc.add(10, 10, 9999, cache_replay=True)
    acc.add(10, 10, 9999, cache_replay=True)
    # 再一次真实调用 120ms
    acc.add(10, 10, 120)

    assert acc.n_cache_replays == 2
    assert acc.model_calls == 4
    assert acc.p95_latency_ms == 120  # 9999 未混入（否则 p95≈9999）
    assert acc.mean_latency_ms == 110

    assert acc.cost_ledger()["n_cache_replays"] == 2

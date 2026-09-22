"""聚合、诊断掉分、机检/Judge 分列（FRAMEWORK §4.4 / §8）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from cnjudbench.scale import fmt2

DIAG_DROP_ALERT = 10.0


@dataclass
class TaskScores:
    task_id: str
    machine: list[float] = field(default_factory=list)
    judge: list[float] = field(default_factory=list)

    def mean_machine(self) -> float | None:
        return sum(self.machine) / len(self.machine) if self.machine else None

    def mean_judge(self) -> float | None:
        return sum(self.judge) / len(self.judge) if self.judge else None


def diagnostic_drop(main: float, diag: float) -> tuple[float, bool]:
    """诊断掉分 = 主集 − 诊断；>10.00 视为 reward hacking 警报。"""
    drop = main - diag
    return drop, drop > DIAG_DROP_ALERT


def combine(machine: float | None, judge: float | None, mode: str = "parallel",
            w_machine: float = 0.7, w_judge: float = 0.3) -> float | None:
    """默认 parallel：不合并，由调用方分列展示。weighted 供显式加权。"""
    if mode == "parallel":
        return machine  # 调用方应分别展示 judge
    if machine is None and judge is None:
        return None
    if machine is None:
        return judge
    if judge is None:
        return machine
    return w_machine * machine + w_judge * judge


def summarize(tasks: list[TaskScores]) -> dict:
    rows = []
    alerts: list[str] = []
    for t in tasks:
        rows.append({
            "task_id": t.task_id,
            "machine_mean": t.mean_machine(),
            "machine_mean_str": fmt2(t.mean_machine()) if t.mean_machine() is not None else "n/a",
            "judge_mean": t.mean_judge(),
            "judge_mean_str": fmt2(t.mean_judge()) if t.mean_judge() is not None else "n/a",
            "n_machine": len(t.machine),
            "n_judge": len(t.judge),
        })
    return {"tasks": rows, "alerts": alerts, "disclaimer":
            "本评测不构成法律意见，不得用于司法裁判、合规放行或当事人决策。"}

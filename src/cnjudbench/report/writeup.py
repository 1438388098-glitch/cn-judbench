"""报告固定段与 limits 骨架（FRAMEWORK §12.1）。"""

from __future__ import annotations

DISCLAIMER = (
    "本评测仅衡量模型在受控题面与工具环境中的行为表现，"
    "不构成法律意见，不得用于司法裁判、合规放行或当事人决策。"
    "分数为 0.00–100.00 的相对度量，不是可用性认证。"
)


def limits_md(*, flip_rate: float | None = None, unknown_in_lawkb: int = 0,
              judge_bias: str = "MockJudge 启发式，正式对比前须换真 Judge 并锁 prompt_hash",
              pending_text_review: list[str] | None = None) -> str:
    pending = ", ".join(pending_text_review or []) or "无"
    fr = "n/a" if flip_rate is None else f"{flip_rate:.4f}"
    return (
        "# limits\n\n"
        f"- 谓词翻转率：{fr}（离线 Mock 期望 0；闭源 API < 5%）\n"
        f"- unknown_in_lawkb 分列数：{unknown_in_lawkb}（不计幻觉）\n"
        f"- Judge：{judge_bias}\n"
        f"- lawkb 待校对：{pending}\n"
        "- Min-K% 等 logit 污染检测仅开源权重。\n\n"
        f"{DISCLAIMER}\n"
    )

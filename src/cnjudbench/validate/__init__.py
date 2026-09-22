"""校验层：适用面矩阵 + 任务包 + 题面 JSONL。"""

from .matrix import check_predicate_set, predicate_allowed, ptp_allowed
from .items import validate_items_dir
from .tasks import validate_tasks

__all__ = [
    "check_predicate_set",
    "predicate_allowed",
    "ptp_allowed",
    "validate_items_dir",
    "validate_tasks",
]

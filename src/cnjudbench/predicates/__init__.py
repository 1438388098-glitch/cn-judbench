"""FTP/PTP 谓词执行器（FRAMEWORK §4.2、附录 B；impl-P0b §3）。"""

from .base import EvalContext, PredicateError, PredicateResult
from .registry import evaluate_predicates

__all__ = ["EvalContext", "PredicateError", "PredicateResult", "evaluate_predicates"]

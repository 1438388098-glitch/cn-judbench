"""模型适配层（FRAMEWORK §7 适配层；impl-P0b §5）。"""

from .base import CompletionResult, ModelAdapter
from .mock import MockAdapter

__all__ = ["CompletionResult", "ModelAdapter", "MockAdapter"]

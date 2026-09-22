"""τ-Jud 对话层：模拟用户、多轮会话、终态 F1、Proto 检查单（impl-P3 §2）。"""

from .proto import PROTO_ITEMS, ProtoResult, check_proto
from .session import DialogTurn, DialogResult, run_dialog
from .state_score import state_f1
from .user_sim import UserSim, pick_persona

__all__ = [
    "PROTO_ITEMS",
    "ProtoResult",
    "check_proto",
    "DialogTurn",
    "DialogResult",
    "run_dialog",
    "state_f1",
    "UserSim",
    "pick_persona",
]

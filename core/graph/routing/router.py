"""Routing logic for learning graph."""

from core.graph.state import LearningState


def route_next_node(state: LearningState) -> str:
    """根据 next_action 选择下一节点分支。"""
    next_action = state["next_action"]
    if next_action == "hint":
        return "hint_node"
    if next_action == "teach":
        return "teach"
    return "end"


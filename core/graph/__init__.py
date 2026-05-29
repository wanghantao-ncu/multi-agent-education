"""Learning graph package entrypoint."""

from core.graph.builder.learning_graph_builder import build_learning_graph
from core.graph.state import LearningState

_learning_graph = None


def get_learning_graph():
    """获取学习状态图单例。"""
    global _learning_graph
    if _learning_graph is None:
        _learning_graph = build_learning_graph()
    return _learning_graph


__all__ = ["LearningState", "build_learning_graph", "get_learning_graph"]


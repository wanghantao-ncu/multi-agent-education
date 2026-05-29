"""Graph state definitions."""
from typing import Any, Dict, Optional, TypedDict


class LearningState(TypedDict):
    """全局学习状态图定义。"""

    learner_id: str
    knowledge_id: str
    question: Optional[str]
    answer: Optional[str]
    is_correct: Optional[bool]
    mastery: float
    attempts: int
    hint_level: int
    next_action: str
    response: Optional[str]
    hint: Optional[str]
    curriculum: Optional[Dict[str, Any]]
    context: Dict[str, Any]


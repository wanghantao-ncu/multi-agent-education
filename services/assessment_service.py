"""
Assessment service：承接评估能力，供 graph 节点直接调用。
"""
from dataclasses import dataclass
from typing import Optional

from config.settings import settings
from core.learner_model_manager import LearnerModelManager


@dataclass
class AssessmentResult:
    """评估结果。"""

    mastery: float
    attempts: int
    next_action: str


class AssessmentService:
    """评估业务服务。"""

    def __init__(self, learner_model_manager: LearnerModelManager) -> None:
        self.learner_model_manager = learner_model_manager

    def assess(
        self,
        learner_id: str,
        knowledge_id: str,
        is_correct: Optional[bool],
        attempts: int = 0,
    ) -> AssessmentResult:
        """
        执行评估逻辑。

        - `is_correct is not None` 时更新掌握度
        - `is_correct is None` 时仅返回当前掌握度快照
        """
        model = self.learner_model_manager.get_or_create_model(learner_id)

        if is_correct is not None:
            state_obj = model.update_mastery(knowledge_id, is_correct)
            overall_progress = model.get_overall_progress()
            recent_accuracy = overall_progress.get("accuracy", 0.5)
            model.update_learning_speed(recent_accuracy)
            mastery = state_obj.mastery
            latest_attempts = state_obj.attempts
        else:
            state_obj = model.get_state(knowledge_id)
            mastery = state_obj.mastery
            latest_attempts = state_obj.attempts if state_obj.attempts is not None else attempts

        if latest_attempts >= 2 and mastery < settings.low_mastery_threshold:
            next_action = "hint"
        else:
            next_action = "teach"

        return AssessmentResult(
            mastery=mastery,
            attempts=latest_attempts,
            next_action=next_action,
        )


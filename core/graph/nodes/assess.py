"""Assess node for learning graph."""
import asyncio
import logging
from time import perf_counter
from dataclasses import dataclass

from core.database import Database
from core.learner_model_manager import LearnerModelManager
from core.observability import record_graph_node_execution
from services.assessment_service import AssessmentService

from core.graph.state import LearningState

logger = logging.getLogger(__name__)


@dataclass
class AssessNodeDeps:
    learner_manager: LearnerModelManager
    assessment_service: AssessmentService
    database: Database


async def assess_node(state: LearningState, deps: AssessNodeDeps) -> LearningState:
    """评估节点：更新掌握度并决定后续分支。"""
    started = perf_counter()
    learner_id = state["learner_id"]
    knowledge_id = state["knowledge_id"]
    trace_id = state.get("context", {}).get("trace_id", "")
    logger.info(
        "[graph.node.assess.start] trace_id=%s learner=%s knowledge=%s",
        trace_id,
        learner_id,
        knowledge_id,
    )

    is_correct = state.get("is_correct")
    current_attempts = state.get("attempts", 0)

    status = "ok"
    try:
        result = deps.assessment_service.assess(
            learner_id=learner_id,
            knowledge_id=knowledge_id,
            is_correct=is_correct,
            attempts=current_attempts,
        )

        if is_correct is not None:
            await asyncio.to_thread(
                deps.database.log_learning_event,
                learner_id,
                knowledge_id,
                "submission",
                {"is_correct": is_correct, "mastery": result.mastery},
            )
            await asyncio.to_thread(deps.learner_manager.save_model, learner_id)

        return {
            **state,
            "mastery": result.mastery,
            "attempts": result.attempts,
            "next_action": result.next_action,
        }
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = (perf_counter() - started) * 1000
        record_graph_node_execution(
            trace_id=trace_id,
            node_name="assess",
            elapsed_ms=elapsed_ms,
            status=status,
            learner_id=learner_id,
            knowledge_id=knowledge_id,
        )
        logger.info(
            "[graph.node.assess.end] trace_id=%s learner=%s knowledge=%s elapsed_ms=%.1f status=%s",
            trace_id,
            learner_id,
            knowledge_id,
            elapsed_ms,
            status,
        )


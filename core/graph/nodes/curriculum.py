"""Curriculum node for learning graph."""
import asyncio
import logging
from time import perf_counter

from services.curriculum_service import CurriculumService

from core.observability import record_graph_node_execution
from core.graph.state import LearningState

logger = logging.getLogger(__name__)

_CURRICULUM_FALLBACK = {
    "next_topic": "",
    "review_due": False,
    "learning_path_reason": "",
}


async def curriculum_node(
    state: LearningState, curriculum_service: CurriculumService
) -> LearningState:
    """课程规划节点：调用 curriculum service 生成学习路径建议。"""
    started = perf_counter()
    learner_id = state["learner_id"]
    knowledge_id = state["knowledge_id"]
    trace_id = state.get("context", {}).get("trace_id", "")
    logger.info(
        "[graph.node.curriculum.start] trace_id=%s learner=%s knowledge=%s",
        trace_id,
        learner_id,
        knowledge_id,
    )
    status = "ok"
    try:
        curriculum = await asyncio.to_thread(
            curriculum_service.plan_curriculum,
            learner_id,
            knowledge_id,
        )
        return {
            **state,
            "curriculum": curriculum,
        }
    except Exception:
        status = "error"
        return {
            **state,
            "curriculum": dict(_CURRICULUM_FALLBACK),
        }
    finally:
        elapsed_ms = (perf_counter() - started) * 1000
        record_graph_node_execution(
            trace_id=trace_id,
            node_name="curriculum",
            elapsed_ms=elapsed_ms,
            status=status,
            learner_id=learner_id,
            knowledge_id=knowledge_id,
        )
        logger.info(
            "[graph.node.curriculum.end] trace_id=%s learner=%s knowledge=%s elapsed_ms=%.1f status=%s",
            trace_id,
            learner_id,
            knowledge_id,
            elapsed_ms,
            status,
        )

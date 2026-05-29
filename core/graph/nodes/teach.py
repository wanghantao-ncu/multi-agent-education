"""Teach node for learning graph."""
import asyncio
import logging
from time import perf_counter

from services.tutor_service import TutorService

from core.observability import record_graph_node_execution
from core.graph.state import LearningState

logger = logging.getLogger(__name__)


async def teach_node(state: LearningState, tutor_service: TutorService) -> LearningState:
    """教学节点：调用 tutor service 生成教学回复。"""
    started = perf_counter()
    learner_id = state["learner_id"]
    knowledge_id = state["knowledge_id"]
    trace_id = state.get("context", {}).get("trace_id", "")
    logger.info(
        "[graph.node.teach.start] trace_id=%s learner=%s knowledge=%s",
        trace_id,
        learner_id,
        knowledge_id,
    )
    status = "ok"
    context = state.get("context", {})
    try:
        response = await asyncio.to_thread(
            tutor_service.generate_response,
            knowledge_id=state["knowledge_id"],
            mastery=state["mastery"],
            is_correct=state.get("is_correct"),
            question=state.get("question", ""),
            chat_history=context.get("chat_history", []),
        )
        return {
            **state,
            "response": response,
            "next_action": "end",
        }
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = (perf_counter() - started) * 1000
        record_graph_node_execution(
            trace_id=trace_id,
            node_name="teach",
            elapsed_ms=elapsed_ms,
            status=status,
            learner_id=learner_id,
            knowledge_id=knowledge_id,
        )
        logger.info(
            "[graph.node.teach.end] trace_id=%s learner=%s knowledge=%s elapsed_ms=%.1f status=%s",
            trace_id,
            learner_id,
            knowledge_id,
            elapsed_ms,
            status,
        )


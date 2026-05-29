"""Hint node for learning graph."""
import asyncio
import logging
from time import perf_counter

from services.hint_service import HintService

from core.observability import record_graph_node_execution
from core.graph.state import LearningState

logger = logging.getLogger(__name__)


async def hint_node(state: LearningState, hint_service: HintService) -> LearningState:
    """提示节点：调用 hint service 生成分级提示。"""
    started = perf_counter()
    learner_id = state["learner_id"]
    knowledge_id = state["knowledge_id"]
    trace_id = state.get("context", {}).get("trace_id", "")
    logger.info(
        "[graph.node.hint.start] trace_id=%s learner=%s knowledge=%s",
        trace_id,
        learner_id,
        knowledge_id,
    )
    status = "ok"
    try:
        hint_text, current_level = await asyncio.to_thread(
            hint_service.generate_hint,
            knowledge_id=state["knowledge_id"],
            mastery=state["mastery"],
            attempts=state["attempts"],
            hint_level=state.get("hint_level", 1),
        )
        return {
            **state,
            "hint": hint_text,
            "hint_level": current_level + 1,
            "response": hint_text,
            "next_action": "end",
        }
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = (perf_counter() - started) * 1000
        record_graph_node_execution(
            trace_id=trace_id,
            node_name="hint",
            elapsed_ms=elapsed_ms,
            status=status,
            learner_id=learner_id,
            knowledge_id=knowledge_id,
        )
        logger.info(
            "[graph.node.hint.end] trace_id=%s learner=%s knowledge=%s elapsed_ms=%.1f status=%s",
            trace_id,
            learner_id,
            knowledge_id,
            elapsed_ms,
            status,
        )


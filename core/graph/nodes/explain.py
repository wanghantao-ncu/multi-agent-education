"""Explain node for learning graph."""
import logging
from time import perf_counter

from core.observability import record_graph_node_execution
from core.graph.state import LearningState

logger = logging.getLogger(__name__)


async def explain_node(state: LearningState) -> LearningState:
    """
    解释节点：本期为轻量收尾节点，保持教学回复不变并标记流程结束。
    后续可在此接入基于 curriculum 的 LLM 补充说明。
    """
    started = perf_counter()
    learner_id = state["learner_id"]
    knowledge_id = state["knowledge_id"]
    trace_id = state.get("context", {}).get("trace_id", "")
    logger.info(
        "[graph.node.explain.start] trace_id=%s learner=%s knowledge=%s",
        trace_id,
        learner_id,
        knowledge_id,
    )
    status = "ok"
    try:
        return {
            **state,
            "next_action": "end",
        }
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = (perf_counter() - started) * 1000
        record_graph_node_execution(
            trace_id=trace_id,
            node_name="explain",
            elapsed_ms=elapsed_ms,
            status=status,
            learner_id=learner_id,
            knowledge_id=knowledge_id,
        )
        logger.info(
            "[graph.node.explain.end] trace_id=%s learner=%s knowledge=%s elapsed_ms=%.1f status=%s",
            trace_id,
            learner_id,
            knowledge_id,
            elapsed_ms,
            status,
        )

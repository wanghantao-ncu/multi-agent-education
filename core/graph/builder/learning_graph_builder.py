"""Graph builder module."""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from core.database import get_database
from core.graph.nodes.assess import AssessNodeDeps, assess_node
from core.graph.nodes.curriculum import curriculum_node
from core.graph.nodes.explain import explain_node
from core.graph.nodes.hint import hint_node
from core.graph.nodes.teach import teach_node
from core.graph.routing.router import route_next_node
from core.graph.state import LearningState
from core.knowledge_graph import build_sample_math_graph
from core.learner_model_manager import get_learner_model_manager
from services.assessment_service import AssessmentService
from services.curriculum_service import CurriculumService
from services.hint_service import HintService
from services.tutor_service import TutorService


def build_learning_graph():
    """构建学习状态图（builder 模块）。"""
    learner_manager = get_learner_model_manager()
    db = get_database()
    deps = AssessNodeDeps(
        learner_manager=learner_manager,
        assessment_service=AssessmentService(learner_manager),
        database=db,
    )
    tutor_service = TutorService()
    hint_service = HintService()
    curriculum_service = CurriculumService(
        learner_model_manager=learner_manager,
        knowledge_graph=build_sample_math_graph(),
        database=db,
    )

    async def _assess(state: LearningState):
        return await assess_node(state, deps)

    async def _teach(state: LearningState):
        return await teach_node(state, tutor_service)

    async def _hint(state: LearningState):
        return await hint_node(state, hint_service)

    async def _plan_curriculum(state: LearningState):
        return await curriculum_node(state, curriculum_service)

    async def _explain(state: LearningState):
        return await explain_node(state)

    builder = StateGraph(LearningState)
    builder.add_node("assess", _assess)
    builder.add_node("teach", _teach)
    builder.add_node("hint_node", _hint)
    builder.add_node("plan_curriculum", _plan_curriculum)
    builder.add_node("explain", _explain)
    builder.set_entry_point("assess")
    builder.add_conditional_edges(
        "assess",
        route_next_node,
        {
            "teach": "teach",
            "hint": "hint_node",
            "end": END,
        },
    )
    builder.add_edge("teach", "plan_curriculum")
    builder.add_edge("hint_node", "plan_curriculum")
    builder.add_edge("plan_curriculum", "explain")
    builder.add_edge("explain", END)
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


"""Integration-style node/service contract tests."""
import asyncio

from core.graph.nodes.assess import AssessNodeDeps, assess_node
from core.graph.nodes.curriculum import curriculum_node
from core.graph.nodes.hint import hint_node
from core.graph.nodes.teach import teach_node
from services.assessment_service import AssessmentResult


class FakeAssessmentService:
    def assess(self, learner_id, knowledge_id, is_correct, attempts):
        return AssessmentResult(mastery=0.42, attempts=attempts + 1, next_action="teach")


class FakeLearnerManager:
    def save_model(self, learner_id):
        return True


class FakeDatabase:
    def log_learning_event(self, learner_id, knowledge_id, event_type, event_data):
        return None


class FakeTutorService:
    def generate_response(self, knowledge_id, mastery, is_correct, question="", chat_history=None):
        return "teaching-response"


class FakeHintService:
    def generate_hint(self, knowledge_id, mastery, attempts, hint_level):
        return "hint-response", 2


class FakeCurriculumService:
    def plan_curriculum(self, learner_id, current_knowledge_id=""):
        return {
            "next_topic": "algebra",
            "review_due": False,
            "learning_path_reason": "ready for next topic",
        }


def test_assess_node_calls_assessment_service_contract():
    deps = AssessNodeDeps(
        learner_manager=FakeLearnerManager(),
        assessment_service=FakeAssessmentService(),
        database=FakeDatabase(),
    )
    state = {
        "learner_id": "u1",
        "knowledge_id": "k1",
        "is_correct": True,
        "mastery": 0.1,
        "attempts": 0,
        "hint_level": 1,
        "next_action": "assess",
        "response": None,
        "hint": None,
        "context": {},
    }

    result = asyncio.run(assess_node(state, deps))

    assert result["mastery"] == 0.42
    assert result["attempts"] == 1
    assert result["next_action"] == "teach"


def test_teach_node_calls_tutor_service_contract():
    state = {
        "learner_id": "u1",
        "knowledge_id": "k1",
        "is_correct": None,
        "mastery": 0.5,
        "attempts": 0,
        "hint_level": 1,
        "next_action": "teach",
        "response": None,
        "hint": None,
        "question": "what is this",
        "context": {"chat_history": [{"role": "user", "content": "hello"}]},
    }

    result = asyncio.run(teach_node(state, FakeTutorService()))

    assert result["response"] == "teaching-response"
    assert result["next_action"] == "end"


def test_hint_node_calls_hint_service_contract():
    state = {
        "learner_id": "u1",
        "knowledge_id": "k1",
        "is_correct": False,
        "mastery": 0.1,
        "attempts": 3,
        "hint_level": 1,
        "next_action": "hint",
        "response": None,
        "hint": None,
        "context": {},
    }

    result = asyncio.run(hint_node(state, FakeHintService()))

    assert result["hint"] == "hint-response"
    assert result["response"] == "hint-response"
    assert result["hint_level"] == 3
    assert result["next_action"] == "end"


def test_curriculum_node_calls_curriculum_service_contract():
    state = {
        "learner_id": "u1",
        "knowledge_id": "k1",
        "is_correct": True,
        "mastery": 0.8,
        "attempts": 1,
        "hint_level": 1,
        "next_action": "teach",
        "response": "already taught",
        "hint": None,
        "context": {},
    }

    result = asyncio.run(curriculum_node(state, FakeCurriculumService()))

    assert result["curriculum"]["next_topic"] == "algebra"
    assert result["curriculum"]["review_due"] is False
    assert result["curriculum"]["learning_path_reason"] == "ready for next topic"
    assert result["response"] == "already taught"


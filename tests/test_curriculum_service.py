"""Unit tests for curriculum service."""

from services.curriculum_service import CurriculumService


class FakeState:
    def __init__(self, knowledge_id: str, mastery: float) -> None:
        self.knowledge_id = knowledge_id
        self.mastery = mastery


class FakeModel:
    def __init__(self, states: list[FakeState]) -> None:
        self.knowledge_states = {s.knowledge_id: s for s in states}


class FakeLearnerManager:
    def __init__(self, model: FakeModel, should_raise: bool = False) -> None:
        self.model = model
        self.should_raise = should_raise

    def get_or_create_model(self, learner_id: str) -> FakeModel:
        if self.should_raise:
            raise RuntimeError("boom")
        return self.model


class FakeKnowledgeGraph:
    def __init__(self, ready_nodes: list[str]) -> None:
        self._ready_nodes = ready_nodes
        self.nodes = {}

    def get_ready_nodes(self, mastered_ids: set[str]) -> list[str]:
        return self._ready_nodes


class FakeDB:
    def __init__(self, payload=None) -> None:
        self.payload = payload
        self.saved: dict[tuple[str, str], dict] = {}

    def load_agent_state(self, agent_name: str, learner_id: str):
        key = (agent_name, learner_id)
        if key in self.saved:
            return self.saved[key]
        return self.payload

    def save_agent_state(self, agent_name: str, learner_id: str, state_data: dict) -> bool:
        self.saved[(agent_name, learner_id)] = state_data
        return True


def test_curriculum_plan_with_suggestion():
    model = FakeModel([FakeState("k1", 0.9)])
    service = CurriculumService(
        learner_model_manager=FakeLearnerManager(model),
        knowledge_graph=FakeKnowledgeGraph(["k2"]),
        database=FakeDB(),
    )

    result = service.plan_curriculum("learner-1", current_knowledge_id="k1")

    assert result["next_topic"] == "k2"
    assert result["review_due"] is False
    assert result["learning_path_reason"] != ""


def test_curriculum_plan_without_suggestion():
    model = FakeModel([FakeState("k1", 0.2)])
    service = CurriculumService(
        learner_model_manager=FakeLearnerManager(model),
        knowledge_graph=FakeKnowledgeGraph([]),
        database=FakeDB(),
    )

    result = service.plan_curriculum("learner-1", current_knowledge_id="k1")

    assert result["next_topic"] == ""
    assert result["review_due"] is False
    assert result["learning_path_reason"] == ""


def test_record_answer_review_persists_item():
    db = FakeDB()
    service = CurriculumService(
        learner_model_manager=FakeLearnerManager(FakeModel([])),
        knowledge_graph=FakeKnowledgeGraph([]),
        database=db,
    )

    service.record_answer_review(
        "learner-1",
        "arithmetic",
        is_correct=True,
        time_spent_seconds=15,
    )
    plan = service.build_review_plan_snapshot("learner-1")

    assert plan["item_count"] == 1
    assert plan["upcoming"][0]["knowledge_id"] == "arithmetic"
    assert plan["upcoming"][0]["repetition"] >= 1


def test_estimate_quality_mapping():
    assert CurriculumService.estimate_quality(True, time_spent_seconds=10) == 5
    assert CurriculumService.estimate_quality(True, time_spent_seconds=60) == 4
    assert CurriculumService.estimate_quality(False, error_type="careless") == 2
    assert CurriculumService.estimate_quality(False, error_type="concept") == 1


def test_curriculum_plan_exception_fallback():
    service = CurriculumService(
        learner_model_manager=FakeLearnerManager(FakeModel([]), should_raise=True),
        knowledge_graph=FakeKnowledgeGraph(["k2"]),
        database=FakeDB(),
    )

    result = service.plan_curriculum("learner-1")

    assert result == {
        "next_topic": "",
        "review_due": False,
        "learning_path_reason": "",
    }


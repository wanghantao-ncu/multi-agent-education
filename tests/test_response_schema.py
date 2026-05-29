"""Response schema contract tests."""

from api.orchestrator import AgentOrchestrator


def _assert_response_schema(payload: dict):
    assert isinstance(payload["response"], str)
    assert isinstance(payload["mastery"], float)
    assert isinstance(payload["next_action"], str)
    assert isinstance(payload["trace_id"], str)
    assert isinstance(payload["curriculum"], dict)
    assert set(payload["curriculum"].keys()) == {
        "next_topic",
        "review_due",
        "learning_path_reason",
    }
    assert isinstance(payload["curriculum"]["next_topic"], str)
    assert isinstance(payload["curriculum"]["review_due"], bool)
    assert isinstance(payload["curriculum"]["learning_path_reason"], str)


def test_submit_answer_response_schema():
    orch = AgentOrchestrator.__new__(AgentOrchestrator)
    result = orch._build_structured_response(
        graph_result={"response": "ok", "mastery": 0.45, "next_action": "teach"},
        curriculum={
            "next_topic": "quadratic_eq",
            "review_due": False,
            "learning_path_reason": "path-reason",
        },
    )
    _assert_response_schema(result)


def test_ask_question_response_schema():
    orch = AgentOrchestrator.__new__(AgentOrchestrator)
    result = orch._build_structured_response(
        graph_result={},
        curriculum={},
    )
    _assert_response_schema(result)
    assert result["curriculum"]["review_due"] is False
    assert result["curriculum"]["next_topic"] == ""
    assert result["curriculum"]["learning_path_reason"] == ""


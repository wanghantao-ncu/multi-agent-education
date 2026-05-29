"""API integration tests for structured response contract."""

from fastapi.testclient import TestClient

from api.main import app


def test_submit_endpoint_returns_structured_response():
    with TestClient(app) as client:
        payload = {
            "learner_id": "u1",
            "knowledge_id": "k1",
            "is_correct": True,
            "time_spent_seconds": 1.0,
        }
        resp = client.post("/api/v1/submit", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "events" not in data
        assert set(data.keys()) == {"response", "mastery", "next_action", "curriculum", "trace_id"}


def test_question_endpoint_returns_structured_response():
    with TestClient(app) as client:
        payload = {
            "learner_id": "u2",
            "knowledge_id": "k1",
            "question": "test question",
        }
        resp = client.post("/api/v1/question", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "events" not in data
        assert set(data.keys()) == {"response", "mastery", "next_action", "curriculum", "trace_id"}


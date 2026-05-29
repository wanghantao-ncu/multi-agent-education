"""Wrong-question notebook API regression tests (no EventBus dependency)."""

from fastapi.testclient import TestClient

from api.main import app


def test_wrong_question_end_to_end_api_flow():
    """Cover upload/recognize/list/detail/practice/delete/count chain."""
    with TestClient(app) as client:
        orch = app.state.orchestrator
        call_log = []

        def fake_upload_wrong_question(**kwargs):
            call_log.append(("upload", kwargs))
            return {
                "success": True,
                "wrong_question_id": 101,
                "question_text": "2x+1=7，求x",
                "knowledge_id": kwargs.get("knowledge_id") or "linear_eq_1",
                "analysis": "移项后两边同除以2。",
            }

        def fake_get_wrong_questions(learner_id, limit=50):
            call_log.append(("list", {"learner_id": learner_id, "limit": limit}))
            return [{"id": 101, "knowledge_id": "linear_eq_1", "question_text": "2x+1=7"}]

        def fake_get_wrong_question_detail(question_id):
            call_log.append(("detail", {"question_id": question_id}))
            return {"id": question_id, "question_text": "2x+1=7", "exercises": [], "practices": []}

        def fake_practice_wrong_question(question_id, learner_id, user_answer, is_correct, time_spent=None):
            call_log.append(
                (
                    "practice",
                    {
                        "question_id": question_id,
                        "learner_id": learner_id,
                        "user_answer": user_answer,
                        "is_correct": is_correct,
                        "time_spent": time_spent,
                    },
                )
            )
            return {"success": True, "message": "练习记录已保存"}

        def fake_delete_wrong_question(question_id):
            call_log.append(("delete", {"question_id": question_id}))
            return True

        def fake_get_wrong_questions_count(learner_id):
            call_log.append(("count", {"learner_id": learner_id}))
            return 1

        orch.upload_wrong_question = fake_upload_wrong_question
        orch.get_wrong_questions = fake_get_wrong_questions
        orch.get_wrong_question_detail = fake_get_wrong_question_detail
        orch.practice_wrong_question = fake_practice_wrong_question
        orch.delete_wrong_question = fake_delete_wrong_question
        orch.get_wrong_questions_count = fake_get_wrong_questions_count

        upload_resp = client.post(
            "/api/v1/wrong-question/upload-base64",
            params={"learner_id": "stu_1", "image_base64": "ZmFrZV9pbWFnZQ=="},
        )
        assert upload_resp.status_code == 200
        assert upload_resp.json()["success"] is True
        assert upload_resp.json()["wrong_question_id"] == 101

        list_resp = client.get("/api/v1/wrong-questions/stu_1")
        assert list_resp.status_code == 200
        assert list_resp.json()["count"] == 1

        detail_resp = client.get("/api/v1/wrong-question/101")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == 101

        practice_resp = client.post(
            "/api/v1/wrong-question/101/practice",
            json={"learner_id": "stu_1", "user_answer": "x=3", "is_correct": True, "time_spent": 18},
        )
        assert practice_resp.status_code == 200
        assert practice_resp.json()["success"] is True

        delete_resp = client.delete("/api/v1/wrong-question/101")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["success"] is True

        count_resp = client.get("/api/v1/wrong-questions/count/stu_1")
        assert count_resp.status_code == 200
        assert count_resp.json()["count"] == 1

        called_steps = [name for name, _ in call_log]
        assert called_steps == ["upload", "list", "detail", "practice", "delete", "count"]

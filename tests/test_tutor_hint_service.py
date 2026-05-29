"""Unit tests for tutor/hint services."""

from services.hint_service import HintService
from services.tutor_service import TutorService


class FakeLLM:
    def __init__(self) -> None:
        self.calls = []

    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000, system_prompt: str | None = None) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "system_prompt": system_prompt,
            }
        )
        return "stub-response"


def test_tutor_service_correct_answer_response():
    llm = FakeLLM()
    service = TutorService(llm_client=llm)

    response = service.generate_response(
        knowledge_id="quadratic_eq",
        mastery=0.7,
        is_correct=True,
    )

    assert response == "stub-response"
    assert "答对了题目" in llm.calls[0]["prompt"]


def test_tutor_service_wrong_answer_response():
    llm = FakeLLM()
    service = TutorService(llm_client=llm)

    response = service.generate_response(
        knowledge_id="quadratic_eq",
        mastery=0.2,
        is_correct=False,
    )

    assert response == "stub-response"
    assert "答错了题目" in llm.calls[0]["prompt"]


def test_tutor_service_question_mode_uses_chat_history():
    llm = FakeLLM()
    service = TutorService(llm_client=llm)

    response = service.generate_response(
        knowledge_id="quadratic_eq",
        mastery=0.5,
        is_correct=None,
        question="为什么要配方？",
        chat_history=[{"role": "user", "content": "我不会"}],
    )

    assert response == "stub-response"
    assert "最近对话" in llm.calls[0]["prompt"]
    assert "我不会" in llm.calls[0]["prompt"]


def test_hint_service_level_1_generation():
    llm = FakeLLM()
    service = HintService(llm_client=llm)

    hint_text, level = service.generate_hint(
        knowledge_id="quadratic_eq",
        mastery=0.5,
        attempts=1,
        hint_level=1,
    )

    assert hint_text == "stub-response"
    assert level == 1


def test_hint_service_level_2_generation():
    llm = FakeLLM()
    service = HintService(llm_client=llm)

    hint_text, level = service.generate_hint(
        knowledge_id="quadratic_eq",
        mastery=0.5,
        attempts=2,
        hint_level=2,
    )

    assert hint_text == "stub-response"
    assert level == 2


def test_hint_service_level_3_generation_for_low_mastery():
    llm = FakeLLM()
    service = HintService(llm_client=llm)

    hint_text, level = service.generate_hint(
        knowledge_id="quadratic_eq",
        mastery=0.1,
        attempts=3,
        hint_level=1,
    )

    assert hint_text == "stub-response"
    assert level == 3


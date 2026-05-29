"""
Tutor service：承接教学回复能力，供 graph 节点直接调用。
"""
from typing import Any, Optional

from core.llm import LLMClient, get_llm_client


class TutorService:
    """教学业务服务。"""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm = llm_client or get_llm_client()

    @staticmethod
    def resolve_level(mastery: float) -> str:
        if mastery < 0.3:
            return "beginner"
        if mastery < 0.6:
            return "developing"
        if mastery < 0.85:
            return "proficient"
        return "mastered"

    @staticmethod
    def _build_system_prompt(level: str) -> str:
        prompts = {
            "beginner": (
                "你是一位耐心的数学老师，学生刚开始学习这个知识点。\n"
                "请用最简单的语言和例子帮助学生理解概念。\n"
                "不要直接给答案，而是通过提问引导学生思考。"
            ),
            "developing": (
                "你是一位苏格拉底式的数学老师，学生正在学习中。\n"
                "请通过提问引导学生思考，不要直接给答案。"
            ),
            "proficient": (
                "你是一位挑战型的数学老师，学生已经比较熟练。\n"
                "请提出更深层的思考问题，引导学生发现知识点之间的联系。"
            ),
            "mastered": (
                "你是一位高级数学导师，学生已掌握此知识点。\n"
                "请引导学生总结归纳方法论，布置综合性挑战题。"
            ),
        }
        return prompts.get(level, prompts["beginner"])

    @staticmethod
    def _build_user_prompt(
        knowledge_id: str,
        mastery: float,
        is_correct: Optional[bool],
        question: str,
        chat_history: list[dict[str, Any]],
    ) -> str:
        if is_correct is True:
            return (
                f"学生在「{knowledge_id}」知识点上答对了题目。\n"
                f"当前掌握度：{mastery:.0%}。\n"
                "请给出鼓励，并提出一个更深入的思考问题。"
            )
        if is_correct is False:
            return (
                f"学生在「{knowledge_id}」知识点上答错了题目。\n"
                f"当前掌握度：{mastery:.0%}。\n"
                "请不要直接告诉答案，而是通过提问引导学生分析错误原因。"
            )
        recent_history = chat_history[-20:] if isinstance(chat_history, list) else []
        history_text = "\n".join(
            f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent_history
        )
        return (
            f"学生关于「{knowledge_id}」的问题是：{question}\n"
            f"最近对话（最多10轮）：\n{history_text if history_text else '（无历史）'}\n"
            "请通过提问引导学生自己思考，不要直接给答案。"
        )

    def generate_response(
        self,
        knowledge_id: str,
        mastery: float,
        is_correct: Optional[bool],
        question: str = "",
        chat_history: Optional[list[dict[str, Any]]] = None,
    ) -> str:
        """生成教学回复。"""
        level = self.resolve_level(mastery)
        system_prompt = self._build_system_prompt(level)
        user_prompt = self._build_user_prompt(
            knowledge_id=knowledge_id,
            mastery=mastery,
            is_correct=is_correct,
            question=question,
            chat_history=chat_history or [],
        )
        return self.llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
        )


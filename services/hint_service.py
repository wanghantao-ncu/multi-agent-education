"""
Hint service：承接提示生成能力，供 graph 节点直接调用。
"""
from core.llm import LLMClient, get_llm_client
from config.settings import settings


class HintService:
    """提示业务服务。"""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or get_llm_client()

    @staticmethod
    def determine_hint_level(mastery: float, attempts: int, hint_level: int) -> int:
        """根据掌握度与尝试次数决定提示级别。"""
        if mastery < settings.low_mastery_threshold and attempts >= 3:
            return 3
        if hint_level <= 1:
            return 1
        if hint_level <= 3:
            return 2
        return 3

    @staticmethod
    def _level_description(level: int) -> str:
        descriptions = {
            1: "元认知暗示：引导学生反思自己的思考过程，不要给出具体步骤",
            2: "脚手架引导：给出关键步骤但不给答案",
            3: "直接提示：给出具体解法（仅在多次尝试后使用）",
        }
        return descriptions[level]

    def generate_hint(self, knowledge_id: str, mastery: float, attempts: int, hint_level: int) -> tuple[str, int]:
        """生成提示文本和本次使用的提示级别。"""
        current_level = self.determine_hint_level(mastery, attempts, hint_level)
        system_prompt = (
            "你是一位数学老师，正在给学生提供提示。\n"
            f"当前提示级别：{current_level} - {self._level_description(current_level)}\n"
            f"知识点：{knowledge_id}\n"
            f"学生掌握度：{mastery:.0%}\n"
            f"尝试次数：{attempts}\n"
        )
        user_prompt = f"请给学生提供一个关于「{knowledge_id}」的提示。"
        hint_text = self.llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.5,
        )
        return hint_text, current_level


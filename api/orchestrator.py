"""API 编排层：入参组装、LangGraph 调用、响应映射与持久化。"""
import asyncio
import logging
from time import perf_counter
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.graph import get_learning_graph
from core.learner_model_manager import get_learner_model_manager
from core.database import get_database
from core.knowledge_graph import build_sample_math_graph
from core.wrong_question_manager import get_wrong_question_manager
from services.curriculum_service import CurriculumService

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Agent编排器（LangGraph版）。"""

    def __init__(self) -> None:
        """初始化编排器。"""
        self.graph = get_learning_graph()
        self.learner_model_manager = get_learner_model_manager()
        self.db = get_database()
        self.knowledge_graph = build_sample_math_graph()
        self.wrong_question_manager = get_wrong_question_manager()
        self.curriculum_service = CurriculumService(
            learner_model_manager=self.learner_model_manager,
            knowledge_graph=self.knowledge_graph,
            database=self.db,
        )

    async def submit_answer(
        self,
        learner_id: str,
        knowledge_id: str,
        is_correct: bool,
        time_spent: float = 0,
        question_text: str = "",
        answer_text: str = "",
        error_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        学生提交答案 -> 触发 LangGraph 学习流程。

        Args:
            learner_id: 学习者ID
            knowledge_id: 知识点ID
            is_correct: 是否正确
            time_spent: 花费时间（秒）

        Returns:
            Dict[str, Any]: 结构化响应
        """
        model = self.learner_model_manager.get_or_create_model(learner_id)
        current_state = model.get_state(knowledge_id)

        trace_id = str(uuid4())
        # 构建初始状态（从真实模型读取，避免固定0.1导致状态错误）
        initial_state = {
            "learner_id": learner_id,
            "knowledge_id": knowledge_id,
            "is_correct": is_correct,
            "question": question_text,
            "answer": answer_text,
            "time_spent_seconds": time_spent,
            "mastery": current_state.mastery,
            "attempts": current_state.attempts,
            "hint_level": 1,
            "next_action": "assess",
            "context": {
                "error_type": (error_type or "unknown").strip().lower() or "unknown",
                "trace_id": trace_id,
            },
        }

        # 配置线程ID（用于记忆）
        config = {"configurable": {"thread_id": learner_id}}

        started = perf_counter()
        # 运行LangGraph
        result = await self.graph.ainvoke(initial_state, config=config)

        # 保存学习历史
        await asyncio.to_thread(
            self.db.add_learning_history,
            learner_id=learner_id,
            knowledge_id=knowledge_id,
            event_type="answer_submitted",
            is_correct=is_correct,
            mastery=result["mastery"],
            time_spent=time_spent,
        )

        # 保存学习者模型状态（修正：只传 model 对象）
        learner_model = self.learner_model_manager.get_or_create_model(learner_id)
        if learner_model:
            await asyncio.to_thread(self.db.save_learner_model, learner_model)

        # 更新 SM-2 复习计划（答题后写入复习条目）
        await asyncio.to_thread(
            self.curriculum_service.record_answer_review,
            learner_id,
            knowledge_id,
            is_correct,
            error_type,
            time_spent,
        )

        elapsed_ms = (perf_counter() - started) * 1000
        logger.info(
            "[orchestrator.submit_answer] trace_id=%s learner=%s knowledge=%s elapsed_ms=%.1f",
            trace_id,
            learner_id,
            knowledge_id,
            elapsed_ms,
        )

        return self._build_structured_response(
            graph_result=result,
            trace_id=trace_id,
        )

    async def ask_question(
        self,
        learner_id: str,
        knowledge_id: str,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        学生提问 -> 触发 LangGraph 问答流程。

        Args:
            learner_id: 学习者ID
            knowledge_id: 知识点ID
            question: 问题内容

        Returns:
            Dict[str, Any]: 结构化响应
        """
        model = self.learner_model_manager.get_or_create_model(learner_id)
        current_state = model.get_state(knowledge_id)

        trace_id = str(uuid4())
        # 构建初始状态（使用当前掌握度）
        initial_state = {
            "learner_id": learner_id,
            "knowledge_id": knowledge_id,
            "question": question,
            "is_correct": None,
            "mastery": current_state.mastery,
            "attempts": current_state.attempts,
            "hint_level": 1,
            "next_action": "assess",
            "context": {
                "chat_history": chat_history or [],
                "trace_id": trace_id,
            }
        }

        # 配置线程ID（用于记忆）
        config = {"configurable": {"thread_id": learner_id}}

        started = perf_counter()
        # 运行LangGraph
        result = await self.graph.ainvoke(initial_state, config=config)

        elapsed_ms = (perf_counter() - started) * 1000
        logger.info(
            "[orchestrator.ask_question] trace_id=%s learner=%s knowledge=%s elapsed_ms=%.1f",
            trace_id,
            learner_id,
            knowledge_id,
            elapsed_ms,
        )
        return self._build_structured_response(
            graph_result=result,
            trace_id=trace_id,
        )

    async def send_message(
        self, learner_id: str, message: str, knowledge_id: str = "general"
    ) -> Dict[str, Any]:
        """
        学生发送消息 -> 触发 LangGraph 对话流程。

        Args:
            learner_id: 学习者ID
            message: 消息内容
            knowledge_id: 知识点ID

        Returns:
            Dict[str, Any]: 结构化响应
        """
        return await self.ask_question(learner_id, knowledge_id, message)

    def _build_structured_response(
        self,
        graph_result: Dict[str, Any],
        curriculum: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """统一响应模型。"""
        if curriculum is None:
            curriculum = graph_result.get("curriculum") or {}
        return {
            "response": graph_result.get("response") or "",
            "mastery": float(graph_result.get("mastery", 0.0)),
            "next_action": graph_result.get("next_action") or "end",
            "curriculum": {
                "next_topic": curriculum.get("next_topic") or "",
                "review_due": bool(curriculum.get("review_due", False)),
                "learning_path_reason": curriculum.get("learning_path_reason") or "",
            },
            "trace_id": trace_id or str(uuid4()),
        }

    def get_learner_progress(self, learner_id: str) -> dict:
        """
        获取学习者进度。

        Args:
            learner_id: 学习者ID

        Returns:
            dict: 学习进度信息
        """
        model = self.learner_model_manager.get_or_create_model(learner_id)
        if not model:
            return {"learner_id": learner_id, "status": "no_data"}

        return {
            "learner_id": learner_id,
            "progress": model.get_overall_progress(),
            "weak_points": [
                {"id": s.knowledge_id, "mastery": s.mastery}
                for s in model.get_weak_points()
            ],
            "strong_points": [
                {"id": s.knowledge_id, "mastery": s.mastery}
                for s in model.get_strong_points()
            ],
        }

    def get_review_plan(self, learner_id: str) -> dict[str, Any]:
        """间隔重复（SM-2）复习计划快照，供前端展示。"""
        if not learner_id.strip():
            return {"learner_id": learner_id, "error": "learner_id 不能为空"}
        return self.curriculum_service.build_review_plan_snapshot(learner_id.strip())

    # ==================== 错题本相关方法（新增）====================

    def upload_wrong_question(
        self,
        learner_id: str,
        image_path: str = None,
        image_base64: str = None,
        knowledge_id: str = None,
        user_answer: str = None,
        error_type: str = "unknown"
    ) -> Dict[str, Any]:
        """
        上传错题图片，识别题目并保存到错题本。

        Args:
            learner_id: 学习者ID
            image_path: 图片文件路径
            image_base64: Base64编码的图片数据
            knowledge_id: 知识点ID（可选）
            user_answer: 用户答案（可选）
            error_type: 错误类型（concept/careless/unknown）

        Returns:
            Dict[str, Any]: 处理结果
        """
        return self.wrong_question_manager.upload_wrong_question(
            learner_id=learner_id,
            image_path=image_path,
            image_base64=image_base64,
            knowledge_id=knowledge_id,
            user_answer=user_answer,
            error_type=error_type
        )

    def get_wrong_questions(self, learner_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取学习者的错题列表。

        Args:
            learner_id: 学习者ID
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 错题列表
        """
        return self.wrong_question_manager.get_wrong_questions(learner_id, limit)

    def get_wrong_question_detail(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        获取错题详情，包括生成的练习题。

        Args:
            question_id: 错题ID

        Returns:
            Optional[Dict[str, Any]]: 错题详情
        """
        return self.wrong_question_manager.get_wrong_question_detail(question_id)

    def practice_wrong_question(
        self,
        question_id: int,
        learner_id: str,
        user_answer: str,
        is_correct: bool,
        time_spent: int = None
    ) -> Dict[str, Any]:
        """
        练习错题，记录答题结果。

        Args:
            question_id: 错题ID
            learner_id: 学习者ID
            user_answer: 用户答案
            is_correct: 是否正确
            time_spent: 用时（秒）

        Returns:
            Dict[str, Any]: 练习结果
        """
        return self.wrong_question_manager.practice_wrong_question(
            question_id=question_id,
            learner_id=learner_id,
            user_answer=user_answer,
            is_correct=is_correct,
            time_spent=time_spent
        )

    def delete_wrong_question(self, question_id: int) -> bool:
        """
        删除错题。

        Args:
            question_id: 错题ID

        Returns:
            bool: 是否成功
        """
        return self.wrong_question_manager.delete_wrong_question(question_id)

    def get_wrong_questions_count(self, learner_id: str) -> int:
        """
        获取学习者的错题数量。

        Args:
            learner_id: 学习者ID

        Returns:
            int: 错题数量
        """
        return self.wrong_question_manager.get_wrong_questions_count(learner_id)

    # ==================== 错题本相关方法结束 ====================
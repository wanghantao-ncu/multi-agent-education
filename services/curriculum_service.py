"""
Curriculum service：承接课程规划与复习计划能力。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from config.settings import settings
from core.database import Database, get_database
from core.knowledge_graph import KnowledgeGraph, build_sample_math_graph
from core.learner_model_manager import LearnerModelManager, get_learner_model_manager
from core.spaced_repetition import ReviewItem, SpacedRepetition


class CurriculumService:
    """课程业务服务。"""

    def __init__(
        self,
        learner_model_manager: Optional[LearnerModelManager] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        spaced_repetition: Optional[SpacedRepetition] = None,
        database: Optional[Database] = None,
    ) -> None:
        self.learner_model_manager = learner_model_manager or get_learner_model_manager()
        self.knowledge_graph = knowledge_graph or build_sample_math_graph()
        self.sr = spaced_repetition or SpacedRepetition()
        self.db = database or get_database()

    def plan_curriculum(self, learner_id: str, current_knowledge_id: str = "") -> dict[str, Any]:
        """
        生成课程建议（用于 graph 节点直调）。

        返回结构稳定，即使异常也提供兜底空值。
        """
        fallback = {
            "next_topic": "",
            "review_due": False,
            "learning_path_reason": "",
        }
        try:
            model = self.learner_model_manager.get_or_create_model(learner_id)
            mastered_ids = {
                s.knowledge_id
                for s in model.knowledge_states.values()
                if s.mastery >= settings.mastery_threshold
            }
            ready = self.knowledge_graph.get_ready_nodes(mastered_ids)
            if ready:
                next_topic = ready[0]
                node = self.knowledge_graph.nodes.get(next_topic)
                return {
                    "next_topic": next_topic,
                    "review_due": False,
                    "learning_path_reason": (
                        f"前置知识已掌握，推荐学习「{node.name if node else next_topic}」"
                    ),
                }

            review = self.build_review_plan_snapshot(learner_id)
            has_due = len(review.get("due", [])) > 0
            if has_due:
                return {
                    "next_topic": current_knowledge_id or "",
                    "review_due": True,
                    "learning_path_reason": "当前无新知识推荐，优先完成到期复习",
                }
            return fallback
        except Exception:
            return fallback

    def _load_review_items(self, learner_id: str) -> list[ReviewItem]:
        payload = self.db.load_agent_state("CurriculumService", learner_id)
        if not payload:
            return []
        items: list[ReviewItem] = []
        raw_items = payload.get("items", {})
        for item_data in raw_items.values():
            try:
                items.append(ReviewItem(**item_data))
            except Exception:
                continue
        return items

    def _save_review_items(self, learner_id: str, items: list[ReviewItem]) -> None:
        payload = {
            "items": {
                item.knowledge_id: item.model_dump(mode="json")
                for item in items
            }
        }
        self.db.save_agent_state("CurriculumService", learner_id, payload)

    @staticmethod
    def estimate_quality(
        is_correct: bool,
        error_type: str | None = None,
        time_spent_seconds: float = 0,
    ) -> int:
        """将答题结果映射为 SM-2 质量分 q∈[0,5]。"""
        if is_correct:
            if time_spent_seconds > 0 and time_spent_seconds <= 20:
                return 5
            return 4
        et = (error_type or "unknown").strip().lower()
        if et == "careless":
            return 2
        if et == "concept":
            return 1
        return 0

    def record_answer_review(
        self,
        learner_id: str,
        knowledge_id: str,
        is_correct: bool,
        error_type: str | None = None,
        time_spent_seconds: float = 0,
    ) -> ReviewItem:
        """答题后更新 SM-2 复习条目并持久化。"""
        items = self._load_review_items(learner_id)
        by_id = {item.knowledge_id: item for item in items}

        item = by_id.get(knowledge_id)
        if item is None:
            item = ReviewItem(knowledge_id=knowledge_id)
            items.append(item)

        was_due = item.is_due
        quality = self.estimate_quality(is_correct, error_type, time_spent_seconds)
        self.sr.review(item, quality)

        if was_due:
            item.due_cycle_log.append(
                {
                    "at": datetime.now().isoformat(timespec="minutes"),
                    "quality": quality,
                    "is_correct": is_correct,
                    "error_type": (error_type or "unknown"),
                    "interval_days": item.interval_days,
                    "next_review": item.next_review.isoformat(timespec="minutes"),
                }
            )
            if len(item.due_cycle_log) > 20:
                item.due_cycle_log = item.due_cycle_log[-20:]

        by_id[knowledge_id] = item
        self._save_review_items(learner_id, list(by_id.values()))
        return item

    def build_review_plan_snapshot(self, learner_id: str) -> dict[str, Any]:
        """供前端/API 拉取的复习计划快照。"""
        items = self._load_review_items(learner_id)
        due_items = self.sr.get_due_items(items)
        schedule = self.sr.get_study_schedule(items, days_ahead=7)
        upcoming = sorted(items, key=lambda x: x.next_review)[:20]

        def _row(item: ReviewItem) -> dict[str, Any]:
            node = self.knowledge_graph.nodes.get(item.knowledge_id)
            return {
                "knowledge_id": item.knowledge_id,
                "name": node.name if node else item.knowledge_id,
                "easiness_factor": round(item.easiness_factor, 4),
                "interval_days": item.interval_days,
                "repetition": item.repetition,
                "next_review": item.next_review.isoformat(timespec="minutes"),
                "is_due": item.is_due,
                "overdue_days": round(item.overdue_days, 2) if item.is_due else 0.0,
                "due_cycle_log": item.due_cycle_log[-8:],
            }

        return {
            "learner_id": learner_id,
            "due": [_row(i) for i in due_items],
            "weekly_schedule": schedule,
            "upcoming": [_row(i) for i in upcoming],
            "item_count": len(items),
        }


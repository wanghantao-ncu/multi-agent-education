"""
多Agent智能学习系统 - Streamlit 交互式前端。
功能：
1. 学生登录
2. 知识点选择
3. 答题界面
4. 实时聊天
5. 学习进度展示
6. 知识图谱可视化
7. 系统监控（掌握度分布）
8. 拍照错题本（新增）
"""
import streamlit as st
import asyncio
import json
import pandas as pd
import plotly.express as px
from datetime import datetime
from pathlib import Path

# 导入核心模块
from api.orchestrator import AgentOrchestrator
from core.knowledge_graph import build_sample_math_graph, KnowledgeGraph, KnowledgeNode
from core.database import get_database
from core.llm import get_llm_client

# 页面配置
st.set_page_config(
    page_title="多Agent智能学习系统",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 移动端适配：隐藏右上角菜单与底部水印 + 输入控件尽量占满宽度
st.markdown(
    "<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} "
    ".stTextInput input, .stTextArea textarea {width: 100% !important;}</style>",
    unsafe_allow_html=True,
)

# 初始化Session State
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = AgentOrchestrator()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "learner_id" not in st.session_state:
    st.session_state.learner_id = "student_001"
if "current_knowledge" not in st.session_state:
    st.session_state.current_knowledge = "arithmetic"
if "show_progress" not in st.session_state:
    st.session_state.show_progress = False
if "generated_question" not in st.session_state:
    st.session_state.generated_question = ""
def _topic_display_name(topic_id: str, knowledge_graph: KnowledgeGraph | None = None) -> str:
    """将知识点 ID 转为展示名称。"""
    if not topic_id:
        return "—"
    kg = knowledge_graph or build_sample_math_graph()
    node = kg.nodes.get(topic_id)
    return node.name if node else topic_id


def _render_structured_result(
    result: dict | None,
    title: str = "结构化响应",
    *,
    show_response: bool = True,
    show_mastery: bool = True,
    show_curriculum: bool = True,
    knowledge_graph: KnowledgeGraph | None = None,
) -> None:
    """统一展示 response/mastery/curriculum；可按场景关闭重复字段。"""
    if not result:
        st.info("暂无结构化响应：请先发起聊天或提交答题。")
        return

    response = result.get("response") or ""
    mastery = result.get("mastery")
    curriculum = result.get("curriculum") or {}

    has_response = show_response and bool(response)
    has_mastery = show_mastery and mastery is not None
    has_curriculum = show_curriculum and bool(curriculum)

    if not (has_response or has_mastery or has_curriculum):
        return

    st.subheader(title)

    if show_response:
        if response:
            st.markdown(response)
        else:
            st.caption("response 为空。")

    if show_mastery:
        if mastery is not None:
            try:
                st.metric("当前掌握度", f"{float(mastery):.0%}")
            except Exception:
                st.caption(f"当前掌握度：{mastery}")
        else:
            st.caption("mastery 为空。")

    if show_curriculum:
        next_topic = (curriculum.get("next_topic") or "").strip()
        review_due = bool(curriculum.get("review_due", False))
        reason = (curriculum.get("learning_path_reason") or "").strip()
        next_label = _topic_display_name(next_topic, knowledge_graph) if next_topic else "—"
        st.markdown(
            f"- **下一步：** {next_label}\n\n"
            f"- **复习到期：** {'是' if review_due else '否'}\n\n"
            f"- **推荐学习：** {reason or '—'}"
        )

# 侧边栏：学生信息与设置
with st.sidebar:
    st.title("🧠 多Agent智能学习系统")
    st.divider()

    # 学生ID输入
    st.session_state.learner_id = st.text_input(
        "👤 学生ID",
        value=st.session_state.learner_id,
        help="输入任意学生ID，系统会自动保存学习进度"
    )

    # 构建知识图谱（确保全局可用）
    knowledge_graph = build_sample_math_graph()
    knowledge_options = list(knowledge_graph.nodes.keys())

    # 知识点选择
    st.session_state.current_knowledge = st.selectbox(
        "📚 选择知识点",
        options=knowledge_options,
        index=knowledge_options.index(
            st.session_state.current_knowledge) if st.session_state.current_knowledge in knowledge_options else 0,
        help="选择你想学习的知识点"
    )

    # 显示当前知识点信息
    if st.session_state.current_knowledge in knowledge_graph.nodes:
        node = knowledge_graph.nodes[st.session_state.current_knowledge]
        st.info(f"**{node.name}**\n\n难度：{'⭐' * int(node.difficulty * 5)}\n\n{node.description}")

    st.divider()

    # 学习进度快速查看
    if st.button("📊 查看我的学习进度", use_container_width=True):
        st.session_state.show_progress = True

    # 清空聊天记录
    if st.button("🗑️ 清空聊天记录", use_container_width=True):
        st.session_state.messages = []
        st.success("聊天记录已清空！")

# 主界面
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 学习聊天", "📝 答题练习", "📊 学习进度", "📡 系统监控", "📕 错题本"])

# --- Tab 1: 学习聊天 ---
with tab1:
    st.header(f"学习聊天 - {st.session_state.current_knowledge}")

    # 显示聊天历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 聊天输入
    if prompt := st.chat_input("问我任何问题，或者告诉我你在学习中遇到的困难..."):
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 调用Agent处理
        with st.chat_message("assistant"):
            with st.spinner("AI老师正在思考..."):
                try:
                    # 运行异步函数
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        st.session_state.orchestrator.ask_question(
                            st.session_state.learner_id,
                            st.session_state.current_knowledge,
                            prompt,
                            chat_history=st.session_state.messages[-20:]
                        )
                    )

                    # 读取统一结构化响应
                    response = result.get("response") or "抱歉，我现在无法回答你的问题。"

                    st.markdown(response)

                    # 添加助手消息
                    st.session_state.messages.append({"role": "assistant", "content": response})

                except Exception as e:
                    st.error(f"发生错误：{str(e)}")

# --- Tab 2: 答题练习 ---
with tab2:
    st.header(f"答题练习 - {st.session_state.current_knowledge}")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("题目")
        question_type = st.radio(
            "题型",
            ("自动", "选择", "填空", "解答"),
            horizontal=True,
        )

        # 自动出题按钮：替代手动输入（仍保留可编辑，以便二次微调）
        if st.button("✨ 自动出题", type="primary", use_container_width=True):
            with st.spinner("正在自动出题..."):
                try:
                    learner_model = st.session_state.orchestrator.learner_model_manager.get_model(
                        st.session_state.learner_id
                    )
                    mastery = 0.1
                    if learner_model:
                        try:
                            mastery = learner_model.get_state(st.session_state.current_knowledge).mastery
                        except Exception:
                            mastery = 0.1

                    kg_node = knowledge_graph.nodes.get(st.session_state.current_knowledge)
                    knowledge_point = (
                        f"{kg_node.name}（{st.session_state.current_knowledge}）" if kg_node else st.session_state.current_knowledge
                    )

                    llm = get_llm_client()
                    st.session_state.generated_question = llm.generate_question(
                        knowledge_point=knowledge_point,
                        mastery=mastery,
                        question_type=question_type,  # type: ignore[arg-type]
                    )
                except Exception as e:
                    st.error(f"自动出题失败：{str(e)}")

        question_text = st.text_area(
            "题目内容（可编辑）",
            height=160,
            value=st.session_state.generated_question,
            placeholder="点击上方「自动出题」生成题目，或在此手动编辑"
        )

        st.subheader("你的答案")
        user_answer = st.text_input("输入你的答案", key="main_answer_input")

        is_correct = st.radio(
            "这道题你答对了吗？",
            ("是的，我答对了", "不，我答错了"),
            index=1,
            key="main_is_correct_radio",
        )

        error_type = "unknown"
        if is_correct == "不，我答错了":
            error_type = st.selectbox(
                "错因（用于 SM-2 质量估计）",
                ("concept", "careless", "unknown"),
                index=0,
                format_func=lambda x: {
                    "concept": "概念不清",
                    "careless": "粗心失误",
                    "unknown": "不确定",
                }[x],
                help="概念错误与粗心会影响复习间隔的计算",
            )

        time_spent = st.number_input(
            "花费时间（秒）",
            min_value=0,
            value=30
        )

        if st.button("🚀 提交答案", type="primary", use_container_width=True):
            if not question_text:
                st.warning("请先输入题目内容！")
            else:
                with st.spinner("AI老师正在批改并分析你的掌握情况..."):
                    try:
                        # 运行异步函数
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(
                            st.session_state.orchestrator.submit_answer(
                                st.session_state.learner_id,
                                st.session_state.current_knowledge,
                                is_correct == "是的，我答对了",
                                time_spent,
                                question_text=question_text,
                                answer_text=user_answer,
                                error_type=error_type if is_correct == "不，我答错了" else None,
                            )
                        )

                        # 显示结果
                        st.success("提交成功！")

                        # 提取并显示关键信息（统一结构化响应）
                        mastery = float(result.get("mastery", 0.0))
                        response = result.get("response", "")

                        # 显示掌握度
                        st.metric(
                            label=f"{knowledge_graph.nodes[st.session_state.current_knowledge].name} 掌握度",
                            value=f"{mastery:.0%}",
                            delta=f"{(mastery - 0.1):+.0%}" if mastery > 0.1 else None
                        )

                        # 显示AI回复（掌握度已在上方 metric 展示，不再重复 response/mastery）
                        if response:
                            st.divider()
                            st.subheader("AI老师的反馈")
                            st.markdown(response)

                        st.divider()
                        _render_structured_result(
                            result,
                            "学习建议",
                            show_response=False,
                            show_mastery=False,
                            knowledge_graph=knowledge_graph,
                        )

                    except Exception as e:
                        st.error(f"发生错误：{str(e)}")

    with col2:
        st.subheader("知识图谱")
        try:
            from streamlit_agraph import agraph, Node, Edge, Config

            # 构建节点和边
            nodes = []
            edges = []
            learner_model = st.session_state.orchestrator.learner_model_manager.get_model(st.session_state.learner_id)

            # 添加所有知识点节点
            for kid, node_data in knowledge_graph.nodes.items():
                # 根据掌握度设置节点颜色
                color = "#97C2FC"  # 默认蓝色
                if learner_model:
                    try:
                        state = learner_model.get_state(kid)
                        mastery = state.mastery
                        if mastery >= 0.85:
                            color = "#00FF00"  # 绿色 - 已掌握
                        elif mastery >= 0.6:
                            color = "#FFFF00"  # 黄色 - 熟练
                        elif mastery >= 0.3:
                            color = "#FFA500"  # 橙色 - 发展中
                        else:
                            color = "#FF0000"  # 红色 - 未掌握
                    except:
                        pass

                nodes.append(Node(
                    id=kid,
                    label=node_data.name,
                    size=25,
                    color=color
                ))

            # 添加知识点之间的边（依赖关系）
            for nid in knowledge_graph.nodes:
                for successor in knowledge_graph.get_successors(nid):
                    edges.append(Edge(
                        source=nid,
                        target=successor,
                        type="CURVE_SMOOTH"
                    ))

            # 配置图谱显示
            config = Config(
                width=300,
                height=300,
                directed=True,
                physics=True,
                hierarchical=False
            )

            # 渲染图谱
            agraph(nodes=nodes, edges=edges, config=config)

            # 显示图例
            st.caption("🟢 已掌握 | 🟡 熟练 | 🟠 发展中 | 🔴 未掌握")

        except ImportError:
            st.error("缺少依赖 streamlit-agraph，请执行：pip install streamlit-agraph")
        except Exception as e:
            st.warning(f"知识图谱加载失败：{str(e)}")
            st.info("不影响学习聊天和答题功能")

# --- Tab 3: 学习进度 ---
with tab3:
    st.header("我的学习进度")

    with st.expander("📅 SM-2 复习计划（间隔重复）", expanded=True):
        st.caption("提交答题后会根据掌握度、耗时与错因更新复习间隔；到期知识点会出现在「今日到期」。")
        plan = st.session_state.orchestrator.get_review_plan(st.session_state.learner_id)
        if plan.get("item_count", 0) == 0:
            st.info("暂无复习记录：请先完成几次「答题练习」，系统将自动生成 SM-2 日程。")
        else:
            due = plan.get("due") or []
            if due:
                st.warning(f"今日/已到期需复习：**{len(due)}** 个知识点")
                st.dataframe(
                    pd.DataFrame(due)[
                        ["name", "next_review", "overdue_days", "interval_days", "easiness_factor", "repetition"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("当前没有已逾期的复习项，保持节奏即可。")

            sched = plan.get("weekly_schedule") or {}
            if sched:
                st.subheader("未来 7 天复习日程")
                sched_rows = [{"日期": d, "知识点数": len(ids), "知识点": "、".join(ids)} for d, ids in sorted(sched.items())]
                st.dataframe(pd.DataFrame(sched_rows), use_container_width=True, hide_index=True)

            up = plan.get("upcoming") or []
            if up:
                st.subheader("即将复习（按时间排序）")
                log_cols = [c for c in ["name", "next_review", "interval_days", "easiness_factor", "repetition", "is_due"] if c in pd.DataFrame(up).columns]
                st.dataframe(pd.DataFrame(up)[log_cols], use_container_width=True, hide_index=True)

            st.subheader("到期后练习反馈（验证间隔重复效果）")
            feedback_rows = [row for row in up[:8] if row.get("due_cycle_log")]
            if feedback_rows:
                for row in feedback_rows:
                    logs = row.get("due_cycle_log") or []
                    st.markdown(f"**{row.get('name')}**")
                    st.json(logs[-5:])
            else:
                st.caption("暂无到期后练习反馈数据。")

    # 获取学习者进度
    progress = st.session_state.orchestrator.get_learner_progress(st.session_state.learner_id)

    if progress.get("status") == "no_data":
        st.info("你还没有开始学习，去答题或提问吧！")
    else:
        # 总体统计
        col1, col2, col3, col4 = st.columns(4)

        overall = progress.get("progress", {})
        with col1:
            st.metric("总知识点数", overall.get("total_knowledge_points", 0))
        with col2:
            st.metric("平均掌握度", f"{overall.get('avg_mastery', 0):.0%}")
        with col3:
            st.metric("总答题数", overall.get("total_attempts", 0))
        with col4:
            st.metric("正确率", f"{overall.get('accuracy', 0):.0%}")

        st.divider()

        # 知识点掌握情况
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("💪 已掌握的知识点")
            strong_points = progress.get("strong_points", [])
            if strong_points:
                for sp in strong_points:
                    node_name = knowledge_graph.nodes.get(sp['id'], sp['id']).name if sp['id'] in knowledge_graph.nodes else sp['id']
                    st.success(f"✅ {node_name} - {sp['mastery']:.0%}")
            else:
                st.info("还没有已掌握的知识点，继续加油！")

        with col2:
            st.subheader("📚 需要加强的知识点")
            weak_points = progress.get("weak_points", [])
            if weak_points:
                for wp in weak_points:
                    node_name = knowledge_graph.nodes.get(wp['id'], wp['id']).name if wp['id'] in knowledge_graph.nodes else wp['id']
                    st.warning(f"⚠️ {node_name} - {wp['mastery']:.0%}")
            else:
                st.success("太棒了！没有需要加强的知识点！")

        st.divider()

        # 学习历史
        st.subheader("📜 最近学习历史")
        db = get_database()
        history = db.get_learning_history(st.session_state.learner_id, limit=20)

        if history:
            history_df = pd.DataFrame(history)
            history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
            history_df = history_df.sort_values("timestamp", ascending=False)

            # 替换知识点ID为名称
            def get_knowledge_name(kid):
                return knowledge_graph.nodes.get(kid, kid).name if kid in knowledge_graph.nodes else kid

            history_df["knowledge_name"] = history_df["knowledge_id"].apply(get_knowledge_name)

            # 显示表格
            st.dataframe(
                history_df[["timestamp", "knowledge_name", "event_type"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("时间"),
                    "knowledge_name": st.column_config.TextColumn("知识点"),
                    "event_type": st.column_config.TextColumn("事件类型")
                }
            )

            # 学习趋势图
            st.subheader("📈 学习趋势")
            if "mastery" in history_df.columns:
                trend_df = history_df.groupby(["timestamp", "knowledge_name"])["mastery"].mean().reset_index()
                fig = px.line(trend_df, x="timestamp", y="mastery", color="knowledge_name",
                              title="知识点掌握度变化", labels={"mastery": "掌握度", "timestamp": "时间"})
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("还没有学习历史记录")

# --- Tab 4: 系统监控（掌握度分布）---
with tab4:
    st.header("📡 系统监控")
    st.caption("当前学习者在各知识点上的掌握度分布。")

    if st.button("🔄 刷新", use_container_width=True):
        st.rerun()

    prog = st.session_state.orchestrator.get_learner_progress(st.session_state.learner_id)
    if prog.get("status") == "no_data":
        st.info("暂无掌握度数据，请先完成答题或聊天。")
    else:
        model = st.session_state.orchestrator.learner_model_manager.get_or_create_model(
            st.session_state.learner_id
        )
        rows = []
        for kid, node in knowledge_graph.nodes.items():
            stt = model.get_state(kid)
            rows.append({"知识点": node.name, "掌握度": float(stt.mastery)})
        mdf = pd.DataFrame(rows).sort_values("掌握度", ascending=True)
        fig_m = px.bar(
            mdf,
            x="掌握度",
            y="知识点",
            orientation="h",
            title=f"掌握度分布（{st.session_state.learner_id}）",
            labels={"掌握度": "掌握度", "知识点": "知识点"},
            range_x=[0, 1],
        )
        fig_m.update_layout(height=max(320, len(mdf) * 36))
        st.plotly_chart(fig_m, use_container_width=True)

# --- Tab 5: 错题本（新增）---
with tab5:
    st.header("📕 拍照错题本")
    st.caption("拍照上传错题，AI自动识别、分析错因、生成巩固练习")

    # 初始化错题本相关的session state
    if "wrong_questions" not in st.session_state:
        st.session_state.wrong_questions = []
    if "selected_question" not in st.session_state:
        st.session_state.selected_question = None
    if "ocr_result" not in st.session_state:
        st.session_state.ocr_result = None

    # 错题统计
    col1, col2 = st.columns(2)
    with col1:
        wrong_count = st.session_state.orchestrator.get_wrong_questions_count(st.session_state.learner_id)
        st.metric("错题总数", wrong_count)
    with col2:
        reviewed_count = sum(1 for q in st.session_state.wrong_questions if q.get("reviewed", False))
        st.metric("已复习", reviewed_count)

    st.divider()

    # 上传错题区域
    st.subheader("📸 上传错题")
    col_upload1, col_upload2 = st.columns(2)
    
    with col_upload1:
        uploaded_file = st.file_uploader("选择图片文件", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            # 显示上传的图片
            st.image(uploaded_file, caption="上传的图片", use_column_width=True)
            
            # 保存图片到临时文件
            import os
            from pathlib import Path
            
            upload_dir = Path("uploads")
            upload_dir.mkdir(exist_ok=True)
            image_path = str(upload_dir / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            
            with open(image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.session_state.uploaded_image_path = image_path

    with col_upload2:
        st.subheader("题目信息")
        user_answer = st.text_input("你的答案（可选）")
        error_type = st.selectbox(
            "错误类型",
            ("unknown", "concept", "careless"),
            index=0,
            format_func=lambda x: {
                "concept": "概念不清",
                "careless": "粗心失误",
                "unknown": "不确定",
            }[x],
        )
        
        if st.button("🚀 上传并识别", type="primary", use_container_width=True):
            if "uploaded_image_path" in st.session_state:
                with st.spinner("正在识别图片中的题目..."):
                    try:
                        result = st.session_state.orchestrator.upload_wrong_question(
                            learner_id=st.session_state.learner_id,
                            image_path=st.session_state.uploaded_image_path,
                            knowledge_id=None,  # 自动分析知识点
                            user_answer=user_answer,
                            error_type=error_type
                        )
                        
                        if result.get("success"):
                            st.success(result.get("message", "上传成功！"))
                            
                            # 显示识别结果
                            st.subheader("识别结果")
                            st.write("**题目文本：**", result.get("question_text"))
                            if result.get("correct_answer"):
                                st.write("**正确答案：**", result.get("correct_answer"))
                            if result.get("analysis"):
                                st.write("**解析：**", result.get("analysis"))
                            
                            # 显示生成的练习题
                            exercises = result.get("exercises", [])
                            if exercises:
                                st.subheader("📝 生成的巩固练习题")
                                for i, ex in enumerate(exercises, 1):
                                    with st.expander(f"练习题 {i}"):
                                        st.write(f"**题目：** {ex.get('question_text')}")
                                        st.write(f"**答案：** {ex.get('correct_answer')}")
                            
                            # 刷新错题列表
                            st.session_state.wrong_questions = st.session_state.orchestrator.get_wrong_questions(
                                st.session_state.learner_id
                            )
                        else:
                            st.error(result.get("error", "上传失败"))
                    
                    except Exception as e:
                        st.error(f"上传失败：{str(e)}")
            else:
                st.warning("请先上传图片")

    st.divider()

    # 错题列表
    st.subheader("📋 我的错题")
    
    # 刷新按钮
    if st.button("🔄 刷新错题列表", use_container_width=True):
        st.session_state.wrong_questions = st.session_state.orchestrator.get_wrong_questions(
            st.session_state.learner_id
        )
    
    # 显示错题列表
    if st.session_state.wrong_questions:
        for question in st.session_state.wrong_questions:
            with st.expander(f"📝 {question.get('question_text', '')[:50]}..."):
                col_q1, col_q2 = st.columns([2, 1])
                
                with col_q1:
                    image_path = question.get("image_path")
                    if image_path:
                        img_file = Path(image_path)
                        if img_file.exists():
                            st.image(str(img_file), caption="原始上传错题图（参考）", use_column_width=True)
                        else:
                            st.caption(f"原图路径不存在：{image_path}")

                    st.write("**题目：**", question.get("question_text"))
                    if question.get("user_answer"):
                        st.write("**你的答案：**", question.get("user_answer"))
                    if question.get("correct_answer"):
                        st.write("**正确答案：**", question.get("correct_answer"))
                    if question.get("analysis"):
                        st.write("**解析：**", question.get("analysis"))
                    if question.get("knowledge_name"):
                        st.write("**知识点：**", question.get("knowledge_name"))
                    if question.get("created_at"):
                        st.write("**添加时间：**", question.get("created_at"))
                
                with col_q2:
                    st.write("**复习次数：**", question.get("review_count", 0))
                    status = "已复习" if question.get("reviewed", False) else "待复习"
                    st.write("**状态：**", status)
                    
                    # 练习按钮
                    if st.button(f"🎯 练习此题", key=f"practice_{question['id']}", use_container_width=True):
                        st.session_state.selected_question = question
                        st.rerun()
    
    else:
        st.info("还没有错题记录，点击上方按钮上传错题吧！")

    # 错题练习详情
    if st.session_state.selected_question:
        question = st.session_state.selected_question
        st.divider()
        st.subheader(f"🎯 练习：{question.get('question_text', '')[:30]}...")
        
        st.write("**题目：**", question.get("question_text"))
        if question.get("correct_answer"):
            st.write("**正确答案：**", question.get("correct_answer"))
        
        user_answer = st.text_input("输入你的答案", key=f"practice_answer_{question['id']}")
        is_correct = st.radio("你答对了吗？", ("是的", "不是"), index=1, key=f"practice_correct_{question['id']}")
        
        if st.button("提交答案", type="primary", use_container_width=True):
            result = st.session_state.orchestrator.practice_wrong_question(
                question_id=question["id"],
                learner_id=st.session_state.learner_id,
                user_answer=user_answer,
                is_correct=(is_correct == "是的")
            )
            
            if result.get("success"):
                st.success("练习记录已保存！")
                # 刷新错题列表
                st.session_state.wrong_questions = st.session_state.orchestrator.get_wrong_questions(
                    st.session_state.learner_id
                )
                # 清除选中的题目
                st.session_state.selected_question = None
            else:
                st.error(result.get("error", "保存失败"))
    
    # 删除错题功能
    st.divider()
    st.subheader("🗑️ 删除错题")
    if st.session_state.wrong_questions:
        question_ids = [(q["id"], q["question_text"][:30] + "...") for q in st.session_state.wrong_questions]
        selected_id = st.selectbox("选择要删除的错题", question_ids, format_func=lambda x: x[1])
        
        if st.button("删除选中的错题", use_container_width=True, type="secondary"):
            if selected_id:
                success = st.session_state.orchestrator.delete_wrong_question(selected_id[0])
                if success:
                    st.success("删除成功！")
                    st.session_state.wrong_questions = st.session_state.orchestrator.get_wrong_questions(
                        st.session_state.learner_id
                    )
                else:
                    st.error("删除失败")

# 自动跳转到进度页面（如果用户点击了快速查看）
if st.session_state.show_progress:
    js = "window.scrollTo(0, 0); document.querySelector('[data-testid=\"stTab\"]:nth-child(3)').click();"
    st.components.v1.html(f"<script>{js}</script>", height=0)
    st.session_state.show_progress = False
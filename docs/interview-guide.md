# 面试指导：多 Agent 智能教育系统

> 适用于本项目面试介绍：LangGraph 编排、FastAPI / Streamlit 入口、BKT 学习者模型、SM-2 复习计划、错题本 OCR、SQLite 持久化与基础可观测性。
>
> 面试时建议按项目真实实现来讲。本项目不是 `5-Agent Mesh + EventBus`，也不是 PostgreSQL / Redis / React / Java / Go 多语言系统。

---

## 目录

- [一、项目定位](#一项目定位)
- [二、简历写法](#二简历写法)
- [三、STAR 讲述模板](#三star-讲述模板)
- [四、面试高频问答](#四面试高频问答)
- [五、技术追问准备](#五技术追问准备)
- [六、面试注意事项](#六面试注意事项)

---

## 一、项目定位

### 一句话介绍

这是一个面向数学学习场景的智能教育系统，核心是用 **LangGraph 状态图** 编排个性化学习流程：学生答题或提问后，系统会更新知识点掌握度，按掌握度选择教学或提示，再生成课程建议和复习计划。

### 当前实现能力

| 能力 | 当前实现 |
|------|----------|
| 学习交互 | Streamlit 前端直连 `AgentOrchestrator`，也支持 FastAPI 接口 |
| 流程编排 | `core/graph/` 使用 LangGraph `StateGraph` 编排 `assess -> teach/hint -> curriculum -> explain` |
| 学习者模型 | `core/learner_model.py` 使用 BKT 追踪知识点 mastery |
| 课程规划 | `services/curriculum_service.py` 结合知识图谱与 SM-2 复习记录推荐下一步 |
| 教学与提示 | `services/tutor_service.py` 和 `services/hint_service.py` 生成苏格拉底式讲解和分级提示 |
| 持久化 | `core/database.py` 使用 SQLite 保存学习者模型、历史、错题和复习数据 |
| 错题本 | 支持图片 / Base64 上传、OCR 识别、错因标注和变式练习 |
| 可观测性 | 请求 `trace_id`、节点耗时记录、监控汇总与单次 Trace 查询 |

### 推荐项目叙事

面试中建议把重点放在“系统如何解决个性化教学问题”，而不是只说“用了哪些技术”：

1. **重构边界**：把 Agent 能力拆成 `services/`，把流程控制放进 `core/graph/`，入口由 `api/orchestrator.py` 统一封装。
2. **统一响应契约**：`submit` / `question` / `message` 都返回 `response`、`mastery`、`next_action`、`curriculum`、`trace_id`。
3. **修正学习状态来源**：流程启动时从真实学习者模型读取 mastery / attempts，而不是每次从固定初始值开始。
4. **补齐学习闭环**：答题后更新 BKT、记录学习历史、写入 SM-2 复习计划，再返回教学或提示。
5. **增强工程可测试性**：增加服务契约、图路由、响应结构和错题 API 回归测试。

---

## 二、简历写法

### 推荐版本（与当前代码一致）

```text
项目名称：多 Agent 智能教育与个性化学习系统
技术栈：Python / LangGraph / FastAPI / Streamlit / SQLite / NetworkX / BKT / SM-2

项目背景：
面向数学学习场景，构建基于 LangGraph 编排的自适应学习系统。融合 BKT 掌握度追踪、苏格拉底式引导教学、DAG 知识图谱与 SM-2 间隔复习，按学生掌握度与尝试次数动态选择讲解或分级提示，并推荐下一知识点与复习计划；配套拍照错题本（OCR 识题、错因标注、错题沉淀与变式练习），将错题从“收藏”延伸为可复习、可巩固的学习闭环；学习者模型与错题数据持久化至 SQLite，支持跨会话加载与进度查询。

1. LangGraph 学习流程编排：设计 AgentOrchestrator 统一入口，以 StateGraph 编排 assess → teach/hint → plan_curriculum → explain 流程；评估、教学、提示、课程规划下沉为 services，节点负责状态流转与可观测性（trace_id、节点耗时）。
2. BKT 学习者模型与状态管理：实现 LearnerModel，按知识点维护 mastery、attempts、alpha/beta 等；答题后由 AssessmentService 更新掌握度，编排层统一组装 LearningState，避免多入口导致状态不一致；模型与学习历史写入 SQLite。
3. 动态路径与间隔复习：CurriculumService 结合知识图谱前置依赖与 SM-2 复习记录，生成 next_topic、review_due 与学习路径说明；答题后同步记录复习条目。
4. 苏格拉底式教学与分级提示：TutorService 按掌握度档位（初学/发展/熟练/掌握）调整 Prompt；HintService 在多次尝试且低掌握度时提供脚手架提示；Streamlit 聊天支持传入最近对话上下文（chat_history）。
5. 拍照错题本与学习闭环：实现 WrongQuestionManager + SQLite 错题域表（wrong_questions / wrong_question_practices / wrong_question_exercises）；上传支持 multipart 文件与 Base64 两种接口（FastAPI）；调用百度 OCR 通用文字识别 API 提取题目文本，结合 LLM 生成解析、正确答案与变式练习题；支持错因标注（concept/careless/unknown）、按学习者分页列表查询、单题详情、练习作答记录与删除；上传后联动 SM-2 复习计划与 BKT 掌握度下调；Streamlit 提供拍照上传与错题列表/练习交互。
6. API 契约与质量保障：submit/question/message 统一返回 response、mastery、next_action、curriculum、trace_id；补充图路由、服务契约与错题接口回归测试。

项目成果（可量化项需有实验/压测数据后再写）：
完成可运行的个性化学习原型，覆盖示例初中数学知识图谱（200+ 知识点 ID）、学习进度与复习计划查询、错题闭环及基础监控 Trace；具备 Streamlit 演示与 FastAPI 集成能力。
```

### 不建议写的内容

不要写这些“项目没有完整实现”的表述：

- “5 个 Agent 通过 EventBus 双向异步通信”
- “支持 1000+ 并发学习者，响应延迟 < 500ms”
- “PostgreSQL + Redis 生产级存储”
- “React 前端 / Java / Go 多语言实现”
- “事件溯源完整审计链路”
- “RAG 教材检索已上线”

可以换成更稳妥的表达：

| 不稳妥说法 | 建议说法 |
|------------|----------|
| 设计 Mesh 多 Agent 架构 | 基于 LangGraph 状态图编排多类教学能力 |
| 使用 PostgreSQL / Redis | 当前使用 SQLite，本地演示部署简单，配置中保留扩展项 |
| 支持海量并发 | 采用 FastAPI 异步接口，具备后续服务化扩展基础 |
| Agent 间事件驱动通信 | 节点共享 `LearningState`，由 Orchestrator 统一触发图执行 |
| 完整生产系统 | 面向智能教育场景的可运行原型，并补齐了测试和工程边界 |

---

## 三、STAR 讲述模板

### 模板 1：项目概述

**S（背景）**  
传统教学系统往往是“千人一面”，学生卡壳时只能看标准答案，缺少根据当前掌握度给出的分层引导。这个项目要解决的是：如何把评估、教学、提示、复习和学习路径推荐串成一个可运行、可测试的个性化学习闭环。

**T（任务）**  
我的目标是设计一套统一编排层：把学习流程梳理清楚，把评估、教学、提示、课程规划拆成明确模块，并让 Streamlit 和 FastAPI 都能复用同一套编排逻辑。

**A（行动）**  
我把入口统一到 `AgentOrchestrator`，由它组装学习者状态并调用 LangGraph；把图节点放到 `core/graph/`，把业务能力抽成 `services/`；答题后通过 BKT 更新 mastery，再进入教学或提示节点，最后生成课程建议和结构化响应。同时我补充了响应契约、图路由和错题本回归测试，保证改动后的行为可验证。

**R（结果）**  
系统形成了一个结构清楚、可运行、可测试的智能教育原型。面试中可以强调：项目的价值不是堆技术名词，而是把业务闭环、工程边界和测试契约结合起来。

### 模板 2：技术难点

**面试口述版本：**

> 这个项目里我遇到的一个主要技术难点是学习状态一致性。因为系统有多个入口，比如学生提交答案、直接提问、发送通用消息，还有错题练习。如果这些入口各自更新学习状态，就很容易出现问题：有的地方更新了 mastery，有的地方没有记录 attempts，有的地方写了复习计划但响应里没有体现，最后前端看到的掌握度和后端真实状态就可能不一致。
>
> 我的解决思路是把状态更新收敛到统一编排层。所有学习类请求先进入 `AgentOrchestrator`，由它读取当前学习者模型，构建统一的 `LearningState`，然后交给 LangGraph 执行。答题场景会带上 `is_correct`，评估节点就更新 BKT mastery 和 attempts；提问场景的 `is_correct` 是空值，评估节点只读取当前掌握度，不误改学习状态。后面教学、提示、课程规划都基于这同一份 state 继续往下走。
>
> 最后我又统一了响应结构，不管内部走的是 teach 还是 hint，接口都返回 `response`、`mastery`、`next_action`、`curriculum` 和 `trace_id`。这样前端不用适配多套格式，测试也能围绕这个契约来写。总结一下，就是用“统一入口 + 统一状态 + 统一响应契约”来解决多入口带来的学习状态不一致问题。

### 模板 3：架构取舍

**S**  
多 Agent 系统有很多编排方式，例如 Mesh、事件驱动和状态图。这个项目的学习流程更适合状态机式编排。

**T**  
需要判断是使用事件总线做异步协作，还是使用 LangGraph 管理明确的学习状态转移。

**A**  
我选择 LangGraph。因为学习流程是一个明确的状态转移问题：先评估，再根据 mastery 和 attempts 路由到教学或提示，再生成课程建议。LangGraph 的 `StateGraph`、条件边和 checkpoint 更贴合这个场景，比强行引入事件总线更简单、更可测试。

**R**  
最终架构更接近“可维护的教学状态流”，而不是为了多 Agent 概念引入额外复杂度。后续如果要扩展到跨服务异步协作，可以再把图节点或服务层拆成消息驱动组件。

---

## 四、面试高频问答

### Q1：介绍一下这个项目

可以这样答：

> 传统教学系统往往是“千人一面”：学生卡壳时只能看标准答案，很难得到符合自己掌握水平的引导；错题也常常只停留在拍照或收藏，缺少后续分析和巩固。所以我做了这个多 Agent 智能教育与个性化学习系统，目标是根据学生真实掌握情况提供教学、提示、复习、学习路径推荐和错题巩固。
>
> 架构上，我没有采用去中心化 Mesh + EventBus，而是用 `AgentOrchestrator` 统一接收 Streamlit 和 FastAPI 请求，再通过 LangGraph 状态图编排评估、教学、提示和课程规划节点。一次答题请求进来后，系统会先读取学生当前知识点状态，用 BKT 更新 mastery 和 attempts，再根据掌握度和尝试次数路由到讲解或分级提示，最后结合 DAG 知识图谱和 SM-2 复习计划生成下一步建议。
>
> 教学策略上，系统采用苏格拉底式引导，根据学生掌握度调整讲解深度，尽量通过暗示、提问和脚手架提示帮助学生思考，而不是直接给标准答案。同时系统支持拍照错题本：上传图片后通过 OCR 提取题目，记录错因和知识点，并可以生成变式练习，把“错题收藏”变成“错题再学习”。工程上我还抽离了 services 层，统一了 API 响应结构，并补充了图路由、响应契约和错题接口测试，让这个项目更适合后续扩展。

### Q2：为什么用 LangGraph？

因为这个项目的核心不是开放式多 Agent 对话，而是“学习状态流转”。每次交互都有明确状态：学习者 ID、知识点、是否答对、当前 mastery、尝试次数、提示等级、上下文。LangGraph 的 `StateGraph` 可以把这些状态在节点之间传递，并通过条件边实现 `teach` 或 `hint` 的路由，比在接口里写一堆 if/else 更清晰，也更方便测试。

### Q3：现在算不算多 Agent？

可以说“是多能力 Agent 化，而不是去中心化 Agent Mesh”。项目中没有独立运行的 5 个 Agent 和 EventBus，而是把评估、教学、提示、课程规划拆成服务和图节点，由 LangGraph 统一编排。这样说更真实，也能体现你理解 Agent 架构不是只能有一种形态。

### Q4：这个项目 LangGraph 的具体流程是什么？

可以这样口述：

> 这个项目里 LangGraph 主要负责把一次学习交互拆成可控的状态流。入口是 `AgentOrchestrator`，比如学生提交答案时，编排器会先从学习者模型里读取当前知识点的 mastery 和 attempts，然后组装成一个统一的 `LearningState`。这个 state 里包含 learner_id、knowledge_id、question、answer、is_correct、mastery、attempts、hint_level、next_action 和 context 等字段。
>
> 图的入口节点是 `assess`。如果是答题场景，`assess` 会调用评估服务，用 BKT 更新 mastery 和 attempts，并根据结果写入 `next_action`；如果是提问场景，`is_correct` 是空值，评估节点只读取当前掌握度，不会误更新学习状态。
>
> 接下来走条件边。路由函数会看 `next_action`：如果是 `teach`，进入教学节点，由 TutorService 生成苏格拉底式讲解；如果是 `hint`，进入提示节点，由 HintService 生成分级提示；如果是 `end`，就直接结束。当前规则是 attempts 大于等于 2 且 mastery 低于阈值时进入 hint，否则进入 teach。
>
> 无论走 teach 还是 hint，后面都会进入 `plan_curriculum` 节点。这个节点会结合学习者模型、知识图谱和复习记录生成课程建议，比如下一知识点、是否需要复习以及推荐原因。最后进入 `explain` 节点，把前面生成的教学内容、提示内容和课程建议整理成最终响应，然后到 END。
>
> 所以我总结这个 LangGraph 流程就是：`assess -> teach/hint -> plan_curriculum -> explain -> END`。它的价值是把学习过程从接口里的 if/else 逻辑，变成了一个可观测、可测试、可扩展的状态图。

### Q5：BKT 在项目里怎么用？

BKT 用来估计学生对某个知识点的掌握概率。答题后，`AssessmentService` 会通过学习者模型更新该知识点的 mastery 和 attempts。系统不是简单地用正确率判断会不会，而是考虑“猜对”和“失误”的可能性，所以更适合教育场景。

回答可以补一句：

> 当前 BKT 是轻量实现，适合原型和规则可解释场景。如果有大规模真实答题序列，可以考虑 DKT、IRT 或融合题目难度的模型。

### Q6：teach 和 hint 怎么路由？

当前规则在评估服务里：如果 `attempts >= 2` 且 `mastery < low_mastery_threshold`，就返回 `hint`；否则返回 `teach`。这个规则的业务含义是：学生已经尝试多次且掌握度很低时，不继续泛泛讲解，而是给更具体的脚手架提示。

### Q7：SM-2 在哪里发挥作用？

答题完成后，编排器会调用课程服务记录复习条目。SM-2 根据答题结果、错因和耗时调整复习间隔，用来决定哪些知识点到期需要复习。课程规划服务还会结合知识图谱，给出下一知识点或复习建议。

### Q8：知识图谱怎么用？

知识图谱描述知识点之间的前置依赖。课程推荐时，系统会优先看前置知识是否掌握，再决定是否推荐新知识点；如果发现当前知识点薄弱，也可以回溯相关前置知识做补救学习。

### Q9：为什么用 SQLite？

这个项目定位是本地可运行的智能教育原型，所以 SQLite 足够简单、部署成本低，也方便 Streamlit 和测试环境直接运行。`settings.py` 中保留了数据库 URL 配置，后续如果要上线或多用户并发，可以迁移到 PostgreSQL，并在学习者模型和复习记录层做适配。

### Q10：这个项目涉及到的数据库表有哪些？

可以这样口述：

> 这个项目当前用 SQLite 做本地持久化，核心表可以按业务分成三类。第一类是学习者模型相关表，主要是 `learner_models` 和 `knowledge_states`。`learner_models` 保存学习者的基础模型信息，比如 learner_id、创建时间、更新时间、总交互次数和 metadata；`knowledge_states` 保存某个学生在某个知识点上的掌握情况，包括 mastery、BKT 里的 alpha / beta、attempts、correct_count、streak 和 last_attempt。这两张表支撑个性化学习的核心状态。
>
> 第二类是过程记录表。`learning_history` 记录学习事件，比如提交答案、掌握度变化、耗时等，用来做学习轨迹和后续分析；`agent_states` 用来持久化不同 Agent 或服务在某个学习者上的状态，避免服务重启后内存状态完全丢失。
>
> 第三类是错题本相关表。`wrong_questions` 保存错题主体，包括 learner_id、knowledge_id、OCR 原文、题目文本、学生答案、正确答案、错因类型、分析结果、图片路径、复习次数等；`wrong_question_practices` 记录某道错题后续练习是否答对、作答内容和耗时；`wrong_question_exercises` 保存基于错题生成的变式练习题和答案。
>
> 所以总结起来，数据库不是只存聊天记录，而是围绕“学习者状态、学习过程、错题巩固”三条线设计的。面试时我会重点讲 `learner_models`、`knowledge_states`、`learning_history` 和三张错题表，因为它们对应了系统的个性化评估、学习追踪和错题闭环。

### Q11：可观测性做了什么？

每次编排会生成 `trace_id`，图节点执行时会记录节点名、耗时、状态、学习者和知识点。FastAPI 提供监控汇总和单次 Trace 查询接口。这样遇到“学生为什么拿到这个提示”时，可以按 `trace_id` 追踪一次请求经过了哪些节点。

### Q12：错题本怎么设计？

错题本能力放在 `wrong_question_manager` 和 API 路由中：支持图片上传或 Base64 上传，通过 OCR 识别题目文本，再保存 learner、知识点、错因、图片路径等信息。之后可以查询错题列表、查看单题、生成变式练习或删除错题。

### Q13：你在项目里最有价值的改动是什么？

建议回答：

> 我觉得最有价值的是把“能跑的 Demo”整理成“能继续开发的结构”。我没有一味追加功能，而是先把入口、图编排、服务层和响应契约理顺，再用测试固定关键行为。这样后续无论是替换 LLM、增加新教学策略，还是把 SQLite 换成 PostgreSQL，都有清晰的落点。

### Q14：如果重新做一次，你会怎么改？

可以答三个层次：

1. **数据层**：把 SQLite 迁移到 PostgreSQL，给学习历史、复习记录和错题增加更完整的索引与迁移脚本。
2. **教学内容层**：引入 RAG，把教材、例题和知识点说明检索进 Prompt，减少 LLM 幻觉。
3. **模型层**：在有真实答题数据后，对比 BKT、IRT、DKT 的效果，并做 A/B 测试验证学习收益。

---

## 五、技术追问准备

### 1. LangGraph 核心概念

| 概念 | 本项目中的对应 |
|------|----------------|
| State | `LearningState`，包含 learner、knowledge、mastery、attempts、context 等 |
| Node | `assess`、`teach`、`hint_node`、`plan_curriculum`、`explain` |
| Edge | 固定边和条件边，控制节点流转 |
| Conditional Edge | `assess` 后根据 `next_action` 路由到 teach / hint / END |
| Checkpoint | 当前使用 `MemorySaver`，支持按 learner thread 保存图执行上下文 |

### 2. BKT 简要公式

答对时：

```text
P(L|correct) = P(L)(1 - S) / [P(L)(1 - S) + (1 - P(L))G]
```

答错时：

```text
P(L|wrong) = P(L)S / [P(L)S + (1 - P(L))(1 - G)]
```

再考虑学习迁移：

```text
P(L_next) = P(L_posterior) + (1 - P(L_posterior))T
```

其中 `G` 是猜测概率，`S` 是失误概率，`T` 是学习转移概率。

### 3. SM-2 简要逻辑

SM-2 用回答质量调整复习间隔和难度因子：

```text
EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
```

如果回答质量较差，就缩短或重置间隔；如果回答质量较好，就按 EF 拉长下次复习时间。面试中不必死背公式，重点讲清“根据表现动态安排复习”。

### 4. 结构化响应为什么重要

统一响应让前端、测试和后续 API 调用方都稳定依赖同一个契约：

```json
{
  "response": "教学或提示文本",
  "mastery": 0.42,
  "next_action": "teach",
  "curriculum": {
    "next_topic": "algebra_basics",
    "review_due": false,
    "learning_path_reason": "前置知识已掌握，推荐学习代数基础"
  },
  "trace_id": "..."
}
```

面试中可以说：这类契约比“接口能返回字符串”更重要，因为它决定了前端展示、监控排查和自动化测试能不能稳定推进。

### 5. 测试怎么覆盖

| 测试方向 | 价值 |
|----------|------|
| 图路由测试 | 确认低掌握度多次尝试会进入 hint |
| 服务契约测试 | 确认节点调用服务层时输入输出稳定 |
| 响应结构测试 | 防止 API 返回字段缺失或类型漂移 |
| 错题 API 回归测试 | 防止上传、查询、练习等接口在重构中损坏 |
| 课程服务测试 | 验证复习计划和路径推荐逻辑 |

### 6. 可能的架构升级路线

如果面试官追问“如何上线”，可以这样分阶段答：

1. **存储升级**：SQLite -> PostgreSQL，增加 Alembic 迁移和连接池。
2. **缓存与会话**：把热点学习者状态、会话上下文放入 Redis。
3. **异步任务**：OCR、LLM 长耗时调用和报表统计放到 Celery / RQ / 消息队列。
4. **服务拆分**：把错题 OCR、课程规划、LLM 教学能力拆成独立服务。
5. **安全治理**：增加鉴权、输入校验、Prompt 注入防护、学习数据脱敏。
6. **评估闭环**：埋点收集学习效果，用 A/B 测试验证不同提示策略。

---

## 六、面试注意事项

### Do

1. **明确说业务目标**：强调你如何围绕个性化教学设计架构、补齐闭环、增强测试。
2. **讲真实边界**：当前是 LangGraph 编排，不是 EventBus Mesh；当前是 SQLite，不是生产级分布式存储。
3. **讲业务闭环**：答题 -> BKT 更新 -> teach/hint -> 课程建议 -> 复习计划 -> 错题沉淀。
4. **讲工程取舍**：为什么先做分层和契约，而不是直接堆新功能。
5. **准备画图**：入口层、编排层、服务层、核心数据层四层图最容易讲清楚。

### Don't

1. **不要夸大实现范围**：关于 `5-Agent Mesh`、`EventBus`、`PostgreSQL`、`Redis`、`React`、`Java/Go` 的描述不要当作已实现能力。
2. **不要虚构指标**：没有压测就不要说 `1000+ 并发`、`<500ms`、`提升 35%`。
3. **不要只报技术名**：说 LangGraph 时要解释它在项目里解决了什么状态流转问题。
4. **不要回避不足**：可以主动说当前项目仍是原型，后续要补鉴权、迁移脚本、真实评估数据和生产部署。
5. **不要把 LLM 当万能答案**：教育系统核心还包括学习者模型、知识图谱、复习策略和可观测性。

### 30 秒版本

> 传统教学系统往往是“千人一面”，学生卡壳时只能看标准答案，错题也缺少后续巩固。我做了一个智能教育系统，用 `AgentOrchestrator + LangGraph` 编排评估、教学、提示和课程规划。学生答题后，系统用 BKT 更新掌握度，再结合知识图谱和 SM-2 生成讲解、分级提示、复习计划和下一步学习建议；错题本还支持 OCR 识别、错因记录和变式练习。

### 2 分钟版本

> 传统教学系统往往是“千人一面”，所有学生看到的内容差不多；学生真正卡壳时，通常只能看标准答案，很难得到适合自己当前水平的引导。错题管理也常常只是拍照收藏，缺少错因分析、复习安排和再练习。所以我做了这个多 Agent 智能教育与个性化学习系统，目标是根据学生的真实掌握情况，动态提供教学、提示、复习、学习路径推荐和错题巩固。
>
> 架构上，我没有采用去中心化 Mesh + EventBus，而是选择更适合学习状态流转的 `AgentOrchestrator + LangGraph + services` 分层。Streamlit 和 FastAPI 都先进入编排器，编排器构建 `LearningState`，再调用 LangGraph 状态图。图里主要有评估、教学、提示、课程规划和解释节点；节点本身尽量只负责流程控制，具体能力下沉到 assessment、tutor、hint、curriculum 等服务层。
>
> 算法和策略上，系统用 BKT 量化学生对每个知识点的 mastery；用 DAG 知识图谱表示知识点前置关系，保证推荐路径不会跳过基础；用 SM-2 根据答题表现安排复习时间。教学上采用苏格拉底式提问，根据 mastery 调整引导深度，优先给暗示、提问和脚手架提示，而不是直接给答案。除此之外，我还做了拍照错题本：学生可以上传错题图片，系统通过 OCR 提取题目文本，保存错因、知识点和图片信息，并支持后续查询和生成变式练习。工程上我统一了 API 响应结构，补充了 trace_id、课程建议字段和相关测试，让项目更接近一个可继续扩展的学习系统。

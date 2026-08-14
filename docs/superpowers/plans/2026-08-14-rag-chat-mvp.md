# 检索问答 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现无会话单次问答：`POST /api/v1/chat/ask` + 前端「智能问答」页，完整 JSON 返回答案与引用。

**Architecture:** `chat` 路由 → `rag_service` 编排（Embedding → Milvus → PG 扩块 → 拼上下文 → DeepSeek）；复用现有 `embedding_service` / `milvus_service` / `expand_chunks_for_retrieval`。

**Tech Stack:** FastAPI, SQLAlchemy, OpenAI SDK（兼容 DeepSeek/百炼）, pymilvus, Vue3 + Ant Design Vue

**设计依据:** [2026-08-14-rag-chat-mvp-design.md](../specs/2026-08-14-rag-chat-mvp-design.md)

## Global Constraints

- 响应格式：`{ "code": 0, "message": "success", "data": ... }`，错误 `data: null`
- 业务 id 不进 URL 路径段；路径固定 `POST /api/v1/chat/ask`
- Vue：`<script setup>`，不加 `lang="ts"`；注释用 `/** */`
- 本阶段不做会话落库、不做流式
- COSINE：`score` 越大越相似，阈值过滤用 `score >= rag_score_threshold`

---

### Task 1: Schema + LLM 服务

**Files:**
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/services/llm_service.py`
- Test: `backend/tests/test_llm_service.py`

- [ ] 定义 `ChatAskRequest` / `ChatReference` / `ChatAskRead`
- [ ] 实现 `LLMService.chat(messages) -> str`（OpenAI 兼容，读 `LLM_*`）
- [ ] 单测 Mock OpenAI client

### Task 2: RAG 编排服务

**Files:**
- Create: `backend/app/services/rag_service.py`
- Test: `backend/tests/test_rag_service.py`

- [ ] `ask_knowledge_base(db, knowledge_base_id, question, ...)` 编排全流程
- [ ] 无命中返回友好 answer + 空 references
- [ ] 知识库不存在返回明确错误供路由映射 404
- [ ] Mock Embedding / Milvus / LLM / expand 的单测

### Task 3: Chat API

**Files:**
- Modify: `backend/app/api/v1/chat.py`
- Test: `backend/tests/test_chat_api.py`
- Modify: `AGENTS.md`（补充问答接口约定）

- [ ] `POST /ask` 接 schema，调 `rag_service`
- [ ] API 测试覆盖：成功、空问题、知识库不存在、无命中

### Task 4: 前端对话页

**Files:**
- Create: `frontend/src/services/chat-service.js`
- Create: `frontend/src/views/ChatPage.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/layouts/AdminLayout.vue`

- [ ] `askQuestion({ knowledgeBaseId, question })`
- [ ] 页面：选知识库、提问、展示答案与引用
- [ ] 菜单增加「智能问答」

### Task 5: 验证

- [ ] 跑后端相关 unittest
- [ ] 手工：对已 `embedded` 知识库提问

---

## 执行说明

本会话采用 **Inline Execution**：按 Task 1→5 顺序实现并自测。

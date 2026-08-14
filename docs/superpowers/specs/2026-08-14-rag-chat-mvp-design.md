# 检索问答 MVP 设计（无会话 + 完整 JSON）

> 日期：2026-08-14  
> 状态：待用户确认后实施  
> 前置：文档向量化第 4 阶段已完成（`embedded` + Milvus）

## 1. 目标

在已向量化知识库上提供 **单次问答**：用户选择知识库并提问，系统检索相关切片、拼上下文，调用 DeepSeek 生成答案，并返回引用片段。

**本阶段不做：**

- 多轮会话落库（`chat_sessions` / `chat_messages`）
- 流式输出（SSE）
- 登录鉴权（沿用第一版显式 `owner_id` / 无登录态风格）

后续可在本接口之上加流式与会话。

## 2. 方案选择

| 方案 | 说明 | 结论 |
|------|------|------|
| **A. 单接口 `/chat/ask`** | Embed → Milvus → 扩块 → LLM 一次完成 | **采用** |
| B. `/retrieve` + `/generate` 拆分 | 便于单独调试 | MVP 偏重，暂不采用 |
| C. 先落库会话再问答 | 为多轮铺路 | 超出当前范围 |

答案返回：**完整 JSON 一次返回**（流式后置）。

## 3. 架构与数据流

```
前端 ChatPage
  → POST /api/v1/chat/ask { knowledge_base_id, question }
    → 校验知识库存在
    → EmbeddingService.embed_query(question)          # 百炼
    → MilvusService.search(kb_id, top_k, threshold) # 向量召回
    → 按 chunk_id 读 PG document_chunks（取权威正文）
    → expand_chunks_for_retrieval（父块扩子块）
    → 按 rag_max_context_chars 截断拼上下文
    → LLM（DeepSeek）生成答案
  ← { answer, references[] }
```

**Embedding：** 阿里云百炼（已有 `EMBEDDING_*`）  
**生成：** DeepSeek（已有 `LLM_*`）  
**向量库：** Milvus collection `document_chunks`  
**切片权威正文：** PostgreSQL `document_chunks`（Milvus 中 content 仅冗余）

## 4. API 约定

### 4.1 路径与风格

- `POST /api/v1/chat/ask`
- 业务 id 放请求体，不写 URL 路径段（与文档 / 知识库管理一致）
- 统一响应：`{ "code": 0, "message": "success", "data": ... }`；错误时 `data: null`

### 4.2 请求体

```json
{
  "knowledge_base_id": 1,
  "question": "请假需要谁审批？"
}
```

校验：

- `knowledge_base_id` > 0，且知识库存在
- `question` 非空，建议最大长度 2000 字符

### 4.3 成功响应 `data`

```json
{
  "answer": "根据知识库内容……",
  "question": "请假需要谁审批？",
  "knowledge_base_id": 1,
  "references": [
    {
      "chunk_id": 951,
      "document_id": 321,
      "chunk_index": 0,
      "score": 0.82,
      "content": "切片正文（可截断预览）"
    }
  ]
}
```

说明：

- `score`：Milvus 返回的相似度（COSINE 距离字段按现有 `milvus_service.search` 映射；前端可原样展示）
- 无命中或过滤后为空：`answer` 返回友好提示（如「未在知识库中找到相关内容」），`references: []`，`code` 仍为 0
- LLM / Embedding / Milvus 故障：`code != 0`，带中文 `message`

### 4.4 配置项（已有，可调）

| 环境变量 | 含义 | 默认 |
|----------|------|------|
| `RAG_TOP_K` | Milvus 召回条数 | 5 |
| `RAG_SCORE_THRESHOLD` | 分数阈值过滤 | 0.3 |
| `RAG_MAX_CONTEXT_CHARS` | 送入 LLM 的上下文上限 | 8000 |

> 注：Milvus COSINE 的 `distance`/`score` 语义以实现为准；过滤时在服务层写清「越大越好还是越小越好」，并与单测约定一致。若现有 `search` 返回的 `score` 语义与阈值方向不一致，实现时在 `rag_service` 内统一转换并注释。

## 5. 后端模块拆分

| 模块 | 职责 |
|------|------|
| `app/services/llm_service.py` | OpenAI 兼容 Chat Completions（DeepSeek） |
| `app/services/rag_service.py` | 编排：检索 → 扩块 → 拼上下文 → 调 LLM |
| `app/schemas/chat.py` | `ChatAskRequest` / `ChatAskRead` / `ChatReference` |
| `app/api/v1/chat.py` | `POST /ask` 路由 |
| 复用 | `embedding_service`、`milvus_service`、`expand_chunks_for_retrieval`、`get_knowledge_base` |

**Prompt 要点（系统提示）：**

- 仅依据提供的上下文回答
- 上下文不足时明确说明「根据现有资料无法确定」
- 不要编造文档中不存在的制度/数据
- 可用中文简要作答

**上下文拼接格式（示例）：**

```
[引用1] document_id=... chunk_id=...
正文...

[引用2] ...
```

## 6. 前端

| 项 | 说明 |
|----|------|
| 路由 | `/chat`，`name: chat`，meta.title「智能问答」 |
| 布局 | `AdminLayout` 增加菜单项 |
| 页面 | `ChatPage.vue`：知识库下拉、问题输入、提交、答案区、引用列表 |
| 服务 | `chat-service.js` → `askQuestion({ knowledgeBaseId, question })` |
| 交互 | 提交中 loading；错误用现有 `normalizeErrorMessage`；无轮询 |

风格：与现有知识库/文档页一致（`page-shell` / Ant Design Vue / `<script setup>` 无 TS）。

## 7. 测试与验收

**后端单测（Mock Embedding / Milvus / LLM）：**

- 知识库不存在 → 404
- 空问题 → 400
- 有命中 → 返回 answer + references
- 无命中 → 友好 answer、references 为空

**手工验收：**

1. 知识库内至少 1 篇 `embedded` 文档  
2. 前端选该知识库提问，得到合理答案与引用  
3. 换无关问题，得到「未找到相关内容」类提示  

## 8. 非目标 / 后续

- 流式 SSE  
- 多轮会话与引用落库  
- Rerank  
- 登录态与按用户隔离检索  

## 9. 决策记录

- 生成模型：DeepSeek（不用 Cursor API）  
- Embedding：百炼  
- 接口风格：与文档管理一致的固定路径 + body id  
- 前端：同步做简单对话页

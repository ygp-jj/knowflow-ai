## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.11+) |
| 关系数据库 | PostgreSQL 16 |
| 向量数据库 | Milvus 2.5 |
| 缓存 / 消息队列 | Redis 7 + Celery |
| 对象存储 | MinIO |
| 配置中心 | etcd |
| LLM | DeepSeek / OpenAI 兼容接口 |
| 依赖管理 | pip + requirements.txt |

数据库，使用了线上的 Neon.tech

---

## 环境要求

- Python 3.11+
- Docker & Docker Compose
- Git

## 编码规范

### 代码注释：使用/**  */,新增的方法、参数、变量需要备注

### Git / PR 备注语言
- `git commit` 提交说明、PR 标题与正文、PR 评论、以及需要人工阅读的备注说明，**一律使用中文**。
- 代码标识符（变量名、函数名、分支名前缀等）仍按既有英文/约定风格，不要求改成中文。

### Git 工作流
- **默认在 `dev` 分支上开发**，不再默认新建功能分支（除非用户明确要求另开分支）。
- **未经用户明确同意，禁止执行 `git push`（含 `-u`、强制推送等）**。
- 本地可正常 `commit`；需要推送远端、创建/更新/合并 PR 时，先征得用户同意后再执行。

### 前端Vue 组件编写
- 必须使用 **`<script setup>`** 语法糖，不再使用 `export default`。
- 所有 `.vue` 文件的 `<script>` 标签 **不要加 `lang="ts"`**，直接写 JavaScript。
- 使用 `ref`、`reactive`、`computed`、`watch` 等 API 时，从 `vue` 导入，不需要类型注解。
- 组件名使用 **PascalCase** (大驼峰)，模板中也用 PascalCase 引用组件。

**正确示例:**
```vue
<template>
  <div>
    <a-button @click="handleClick">点击</a-button>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { AButton } from 'ant-design-vue';

const count = ref(0);

function handleClick() {
  count.value++;
}
</script>

<style scoped>
</style>
```

## 后端知识库管理接口约定

- 知识库归属以 **JWT 当前用户** 为准，前端不再传 `owner_id`。
- 知识库管理只实现基础 CRUD：创建、分页列表、详情、修改、删除。
- 知识库接口不要把业务 `id` 写在 URL 路径段里，详情和删除用查询参数传入 `id`，修改用请求体传入 `id`。
- 知识库接口路径固定为：
  - `POST /api/v1/knowledge-bases/create`
  - `GET /api/v1/knowledge-bases/list?page=1&page_size=10`
  - `GET /api/v1/knowledge-bases/detail?id=1`
  - `PUT /api/v1/knowledge-bases/update`
  - `DELETE /api/v1/knowledge-bases/delete?id=1`
- 知识库接口统一响应格式为 `{ "code": 0, "message": "success", "data": ... }`，错误时 `data` 返回 `null`。
- 知识库列表必须分页，返回 `items`、`total`、`page`、`page_size`。
- 删除知识库前必须检查是否存在关联文档；如果存在文档，接口返回错误，不执行删除。
- 知识库 / 文档 / 聊天业务 API 均需 `Authorization: Bearer <token>`（公开接口仅 `/api/v1/auth/login` 与 `/health`）。

## 后端登录鉴权约定

- `POST /api/v1/auth/login`：`{ username, password }` → `{ access_token, token_type, user }`。
- `GET /api/v1/auth/me`：需 Bearer，返回当前用户。
- 演示账号：`hr_admin` / `demo123456`（seed 中 4 用户密码统一，bcrypt）。
- 配置：`JWT_SECRET_KEY` / `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES`（默认 7 天）。
- 设计说明：`backend/docs/2026-08-24-auth-login-design.md`

## 后端文档管理接口约定

- 第一版文档管理采用与知识库管理一致的接口风格，URL 中不要写动态参数。
- 文档创建接口使用 `multipart/form-data`，前端通过 `knowledge_base_id` 和 `file` 上传文档。
- 文档管理接口路径固定为：
  - `POST /api/v1/documents/create`
  - `GET /api/v1/documents/list?page=1&page_size=10`
  - `GET /api/v1/documents/detail?id=1`
  - `PUT /api/v1/documents/update`
  - `DELETE /api/v1/documents/delete?id=1`
  - `GET /api/v1/documents/download?id=1`
  - `GET /api/v1/documents/chunks?document_id=1&page=1&page_size=10`
  - `POST /api/v1/documents/chunk`（请求体 `{ "id": 1 }`，手动触发解析切片）
- 文档列表支持可选 `knowledge_base_id` 过滤，并返回分页结构 `items`、`total`、`page`、`page_size`。
- 文档统一响应格式为 `{ "code": 0, "message": "success", "data": ... }`，错误时 `data` 返回 `null`。
- 文档文件在开发阶段直接存入本地 Docker 启动的 MinIO。
- 删除文档时必须同时删除数据库记录和 MinIO 对象。
- 下载文档时通过后端下载接口返回文件流，不直接暴露 MinIO 真实对象地址。

## 后端文档向量化约定（第 4 阶段）

- **切片不自动向量化**：切片成功终态仍为 `chunked`；需前端手动触发向量化。
- **手动触发向量化**：`POST /api/v1/documents/embed`，请求体 `{ "id": 1 }`，再投递 Celery 任务。
- 文档状态流转：`chunked → embedding → embedded`；失败为 `failed` 并写入 `error_message`。
- 允许再次向量化的状态：`chunked` / `embedded` / `failed`（且 `chunk_count > 0`）。
- Embedding 使用 OpenAI 兼容接口（`EMBEDDING_*`）；向量写入 Milvus（`MILVUS_*`）。
- Milvus 主键与 PG `document_chunks.id` 对齐；回填 `document_chunks.vector_id = str(chunk_id)`。
- 重新向量化前先按 `document_id` 清理旧向量；删除文档时 best-effort 清理 Milvus。
- 列表页仍不做状态轮询；用户点击「刷新」查看 `embedding` / `embedded` / `failed`。
- 父块与子块均需写入向量，便于后续检索命中父块后再扩子块。

## 后端检索问答约定（MVP）

- **无会话单次问答（非流式兜底）**：`POST /api/v1/chat/ask`，请求体 `{ "knowledge_base_id": 1, "question": "..." }`。
- **无会话流式问答（5A）**：`POST /api/v1/chat/ask-stream`，SSE 事件：`references` → `token*` → `done` / `error`。
- **多轮会话（5B）**：
  - 会话：`POST/GET/PUT/DELETE` → `/api/v1/chat/sessions/create|list|detail|update|delete`（`user_id` 由 JWT 注入；创建绑定 `knowledge_base_id`，会话内不可换库）。
  - 消息：`GET /api/v1/chat/messages/list?session_id=`（assistant 带 references）。
  - 提问（唯一）：`POST /api/v1/chat/sessions/ask-stream`，body `{ "session_id", "question" }`；**不做** `sessions/ask`。
  - 落库：先写 user；成功再写 assistant+引用；失败/停止不落 assistant。无命中时 user+友好提示 assistant 都落。
  - 标题：默认「新会话」；仅默认值可被首问自动截断覆盖；支持 `sessions/update` 手动改名。
  - 历史：最近 `CHAT_HISTORY_MAX_MESSAGES`（默认 10）条，再受 `CHAT_HISTORY_MAX_CHARS`（默认 4000）截断；检索上下文仍用 `RAG_MAX_CONTEXT_CHARS`。
- 流程：问题 Embedding → Milvus Top-K（按知识库过滤）→ 父子块扩展 → 拼上下文 → DeepSeek 生成。
- 非流式统一响应 `{ "code": 0, "message": "success", "data": { "answer", "question", "knowledge_base_id", "references" } }`。
- 无命中时友好提示；流式同样先推空 references 再推提示文本。
- 参数：`RAG_TOP_K` / `RAG_SCORE_THRESHOLD` / `RAG_MAX_CONTEXT_CHARS` / `CHAT_HISTORY_MAX_CHARS` / `CHAT_HISTORY_MAX_MESSAGES`。
- 设计说明：`backend/docs/2026-08-21-chat-stream-session-design.md`

## 后端文档解析与切片约定（第 3 阶段 / 方案 A）

- **上传不自动切片**：`POST /create` 仅落库并设为 `uploaded`。
- **手动触发切片**：前端点击「切片」后调用 `POST /api/v1/documents/chunk`，再投递 Celery 任务。
- 列表页**不做状态轮询**（决策 A）；用户点击「刷新」查看进度。
- 本阶段成功终态为 `chunked`（切片完成，待向量化）；**不要**在本阶段写入 Milvus。
- 文档状态流转：`uploaded → parsing → chunking → chunked`；失败为 `failed` 并写入 `error_message`。
- 第 4 阶段：`chunked → embedding → embedded`（决策 B：统一使用 `embedded` 作为向量化完成终态，不再使用 `indexed`）。
- 切片结果写入 `document_chunks`，并更新 `documents.chunk_count`；`vector_id` 本阶段保持为空。
- MVP 切片参数（精准问答）：`chunk_size=256`，`chunk_overlap=50`（字符）；可通过环境变量 `CHUNK_SIZE` / `CHUNK_OVERLAP` 覆盖。
- 本阶段支持解析：PDF / DOCX / TXT / Markdown；不支持类型任务失败。
- 接口路径维持现有风格（决策 C）：业务 id 不写进 URL 路径段。
- 切片列表接口：`GET /api/v1/documents/chunks?document_id=<id>&page=1&page_size=10`。
- 详细设计与任务拆分见：
  - `backend/docs/chunking-service-requirements.md`
  - `backend/docs/phase3-document-parse-chunk-design.md`
  - `docs/phase3-document-parse-chunk-plan.md`
  - `docs/phase3-document-parse-chunk-usage.md`

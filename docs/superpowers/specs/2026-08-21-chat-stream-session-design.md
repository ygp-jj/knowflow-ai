# 第 5 阶段设计：流式输出（5A）+ 多轮会话（5B）

> 日期：2026-08-21  
> 状态：待确认后实施  
> 前置：无会话单次问答 MVP 已完成（`POST /api/v1/chat/ask`）  
> 决策依据：先 5A 后 5B；多轮携带最近 **10** 条消息；旧 `/chat/ask` **保留**作非流式兜底

## 1. 目标

| 期 | 目标 | 不做 |
|----|------|------|
| **5A** | SSE 流式返回答案，前端打字机展示；结束后展示引用 | 会话落库、多轮 |
| **5B** | 会话 CRUD + 会话内追问（流式优先）+ 消息/引用落库 | 登录鉴权、Rerank、问题改写 |

## 2. 总体原则

- 接口风格与现有约定一致：业务 id 不进 URL 路径段；统一 `{ code, message, data }`（SSE 为事件流，另约定）
- Embedding：百炼；生成：DeepSeek（OpenAI 兼容）
- 检索：仍按**当前用户问题**做 Embedding + Milvus；生成阶段再拼「检索上下文 + 对话历史」
- COSINE：`score >= RAG_SCORE_THRESHOLD` 保留

## 3. 第 5A 期：流式输出

### 3.1 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/ask` | **保留**：完整 JSON，便于调试与兼容 |
| POST | `/api/v1/chat/ask-stream` | **新增**：SSE 流式问答 |

**请求体（与 `/ask` 相同）：**

```json
{
  "knowledge_base_id": 1,
  "question": "年休假怎么计算天数？"
}
```

### 3.2 SSE 事件约定

Content-Type: `text/event-stream`

| event | data 示例 | 说明 |
|-------|-----------|------|
| `token` | `{"text":"根据"}` | 增量文本 |
| `references` | `{"references":[...]}` | 检索引用（可在开流前或结束后发；推荐**开流前**发，前端可先展示来源） |
| `done` | `{"ok":true}` | 正常结束 |
| `error` | `{"message":"..."}` | 失败；前端停止渲染并提示 |

推荐时序：

1. 同步完成：校验 KB → Embed → Milvus → 扩块 → 拼上下文  
2. 若无命中：可发一条 `token`（友好提示）+ 空 `references` + `done`，或退回与 `/ask` 相同文案  
3. 有命中：先 `references`，再流式 `token`，最后 `done`  
4. LLM 中途失败：发 `error`（已推送的 token 前端可保留并标注「生成中断」）

### 3.3 后端改动要点

- `llm_service`：增加 `chat_stream(messages) -> Iterator[str]`
- `rag_service`：抽出「检索 + 拼上下文」与「调 LLM」；流式路径复用检索，流式调用 LLM
- `chat.py`：`StreamingResponse` + SSE 封装；注意关闭代理缓冲头 `X-Accel-Buffering: no`（若经 Nginx）

### 3.4 前端改动要点

- `chat-service.js`：`askQuestionStream(...)`，用 `fetch` + `ReadableStream` 解析 SSE（或 `EventSource` 若改为 GET；本期 POST + fetch）
- `ChatPage.vue`：默认走流式；答案区增量追加；结束后渲染引用
- 可选：保留「非流式」开关，内部仍调 `/ask`（非必须）

### 3.5 5A 验收

- [ ] 同一问题，流式最终文本与 `/ask` 语义接近  
- [ ] 前端可见逐字输出  
- [ ] 引用在结束后正确展示  
- [ ] Embedding/Milvus/LLM 失败有 `error` 事件与前端提示  
- [ ] 单测：Mock 流式 LLM；路由冒烟

---

## 4. 第 5B 期：多轮会话

### 4.1 数据表（已有 Neon 脚本）

复用：

- `chat_sessions`：`knowledge_base_id`、`user_id`、`title`
- `chat_messages`：`session_id`、`role`（user/assistant/system）、`content`、`token_count`
- `chat_references`：挂在 **assistant** 消息上

第一版 `user_id` 由前端显式传入（与 `DEFAULT_OWNER_ID` / 知识库 `owner_id` 联调方式一致）。

### 4.2 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/sessions/create` | 创建会话 |
| GET | `/api/v1/chat/sessions/list` | 分页列表（`user_id`） |
| GET | `/api/v1/chat/sessions/detail` | 详情（`id` + `user_id`） |
| DELETE | `/api/v1/chat/sessions/delete` | 删除（级联消息与引用） |
| GET | `/api/v1/chat/messages/list` | 消息分页（含 references） |
| POST | `/api/v1/chat/sessions/ask` | 会话内非流式提问 |
| POST | `/api/v1/chat/sessions/ask-stream` | 会话内流式提问（**默认推荐**） |

**会话内提问请求体示例：**

```json
{
  "session_id": 1,
  "user_id": 101,
  "question": "那病假工资怎么算？"
}
```

### 4.3 多轮上下文策略（已拍板）

- 生成时携带该会话 **最近 10 条** `chat_messages`（按时间正序喂给 LLM）  
- 另附本轮【检索上下文】（仅基于当前 `question` 检索）  
- 系统提示仍要求「依据检索资料作答，不足则说明无法确定」  
- 超长时：先保证检索上下文优先，再截断更早的历史（或整体受 `RAG_MAX_CONTEXT_CHARS` / 独立 `CHAT_HISTORY_MAX_CHARS` 约束；实现时二选一并写进配置）

### 4.4 落库时序（流式）

1. 校验 session 归属  
2. 写入 user message  
3. 检索 + 加载最近 10 条历史  
4. 流式生成；成功后写入 assistant message + references  
5. 若流式失败：**不落** assistant（或落一条带错误说明的系统消息——推荐不落 assistant，仅返回 `error`）  
6. 会话首条用户问题可截断写入/更新 `title`

### 4.5 前端

- 左侧：会话列表（新建 / 删除 / 切换）  
- 右侧：消息流 + 流式气泡 + 引用  
- 新建会话：选知识库 → `sessions/create` → 进入对话  
- 默认调用 `sessions/ask-stream`

### 4.6 与旧 `/chat/ask` 的关系

| 接口 | 定位 |
|------|------|
| `/chat/ask` | **保留**：无会话、完整 JSON；联调、脚本、失败对比 |
| `/chat/ask-stream` | 无会话流式（5A） |
| `/chat/sessions/ask-stream` | 产品主路径（5B） |

前端「智能问答」页在 5B 完成后以会话流式为主；无会话入口可保留为「快速提问」或隐藏到次要入口（实现时按产品选择，默认：**会话为主，无会话接口仅 API 保留**）。

### 4.7 5B 验收

- [ ] 创建/列表/删除会话正常  
- [ ] 同会话追问能利用最近 10 条历史理解指代  
- [ ] 刷新后历史与引用仍在  
- [ ] 流式失败不产生半截 assistant 记录（按约定）  
- [ ] ORM + API 单测（Mock LLM/Embedding/Milvus）

---

## 5. 实施顺序与产出

1. 写 5A 实现计划 → 实现流式 → 联调前端  
2. 写 5B 实现计划 → ORM/Service/API → 改造 ChatPage  
3. 更新 `AGENTS.md` 约定  

## 6. 非目标（本阶段仍不做）

- 登录态 / JWT  
- Rerank、HyDE、问题改写  
- 评测集自动跑分  
- 上传时强制向量化闸门（可另开小需求：问答页提示未 embedded 文档数）

## 7. 决策记录

| 项 | 结论 |
|----|------|
| 分期 | 先 5A 流式 → 再 5B 多轮 |
| 历史条数 | 最近 **10** 条消息 |
| `/chat/ask` | **保留**作非流式兜底与兼容 |
| 产品默认路径 | 5B 后以会话流式为主 |

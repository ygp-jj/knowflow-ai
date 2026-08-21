# 第 5 阶段设计：流式输出（5A）+ 多轮会话（5B）

> 日期：2026-08-21  
> 状态：5A 已完成；5B 决策已确认，待写实现计划后实施  
> 前置：无会话单次问答 MVP + 5A 流式（`/chat/ask`、`/chat/ask-stream`）  
> 文档副本：`backend/docs/`（主阅）与 `docs/superpowers/specs/`（同步）

## 1. 目标

| 期 | 目标 | 不做 |
|----|------|------|
| **5A** | SSE 流式返回答案，前端打字机展示；结束后展示引用 | 会话落库、多轮 |
| **5B** | 会话 CRUD + 会话内流式追问 + 消息/引用落库 + 停止生成 | 登录鉴权、Rerank、问题改写、会话内非流式 ask |

## 2. 总体原则

- 接口风格与现有约定一致：业务 id 不进 URL 路径段；统一 `{ code, message, data }`（SSE 为事件流，另约定）
- Embedding：百炼；生成：DeepSeek（OpenAI 兼容）
- 检索：仍按**当前用户问题**做 Embedding + Milvus；生成阶段再拼「检索上下文 + 对话历史」
- COSINE：`score >= RAG_SCORE_THRESHOLD` 保留
- 实现路径：**方案 A**——在现有 chat 域扩展路由/服务；原地改造 `ChatPage.vue`

## 3. 第 5A 期：流式输出（已完成）

### 3.1 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/ask` | **保留**：完整 JSON，便于调试与兼容 |
| POST | `/api/v1/chat/ask-stream` | SSE 流式问答（无会话） |

SSE 事件：`references` → `token*` → `done` / `error`。

### 3.2 5A 验收（回顾）

- [x] 流式接口与前端打字机
- [x] 引用先推后展示
- [x] Mock 单测与路由冒烟

---

## 4. 第 5B 期：多轮会话（已确认）

### 4.1 数据表（已有 Neon 脚本）

复用：

- `chat_sessions`：`knowledge_base_id`、`user_id`、`title`
- `chat_messages`：`session_id`、`role`（user/assistant/system）、`content`、`token_count`
- `chat_references`：挂在 **assistant** 消息上

约定：

- 第一版 `user_id` 由前端显式传入（与 `DEFAULT_OWNER_ID` / 知识库 `owner_id` 一致）
- 创建会话时绑定知识库，**会话内不可换库**
- `token_count` = `len(content)`（字符粗算）
- 删除会话走 DB **CASCADE**（消息与引用一并删）
- 引用行仅在有检索命中时写入；`score` 用检索分。文档/切片日后被删导致引用级联消失时，消息列表容忍无 `references`

### 4.2 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/sessions/create` | body：`user_id`、`knowledge_base_id`；可选 `title`（缺省「新会话」） |
| GET | `/api/v1/chat/sessions/list` | `user_id` + 分页 → `items/total/page/page_size` |
| GET | `/api/v1/chat/sessions/detail` | `id` + `user_id` |
| PUT | `/api/v1/chat/sessions/update` | body：`id`、`user_id`、`title`（手动改名） |
| DELETE | `/api/v1/chat/sessions/delete` | `id` + `user_id`；级联删消息与引用 |
| GET | `/api/v1/chat/messages/list` | `session_id` + `user_id` + 分页；assistant 带 `references` |
| POST | `/api/v1/chat/sessions/ask-stream` | 会话内流式提问（**唯一**会话提问入口） |

**不做：** `POST /chat/sessions/ask`（会话非流式）。调试用完整 JSON 继续用无会话 `/chat/ask`。

**会话内提问请求体：**

```json
{
  "session_id": 1,
  "user_id": 101,
  "question": "那病假工资怎么算？"
}
```

知识库 id 取自会话记录，不在请求体重复传递。

SSE 与 5A 相同：`references` → `token*` → `done` / `error`。

### 4.3 多轮上下文策略

- 生成时携带该会话 **最近 10 条** `chat_messages`（按时间正序喂给 LLM）
- 另附本轮【检索上下文】（仅基于当前 `question` 检索）
- 系统提示仍要求「依据检索资料作答，不足则说明无法确定」
- 限额分开：
  - 检索上下文：`RAG_MAX_CONTEXT_CHARS`（现默认 8000）
  - 对话历史：`CHAT_HISTORY_MAX_CHARS`（默认 **4000**）；超长时从**更早**的消息截断
- 拼进 LLM 时：检索上下文与历史均保留；两者各自在上述限额内截断，互不挤占

### 4.4 落库与停止时序（`sessions/ask-stream`）

1. 校验 session 存在且 `user_id` 匹配；使用会话上的 `knowledge_base_id`
2. **先写 user message**（`token_count = len(content)`）
3. **自动 title**：仅当当前 `title` 仍为创建默认值「新会话」时，用本条用户问题截断更新；已手动改过的 title 不覆盖
4. 按本轮 `question`：Embed → Milvus → 扩块 → 拼检索上下文
5. 加载最近 10 条消息（含刚写入的 user），再按 `CHAT_HISTORY_MAX_CHARS` 截断历史
6. 先推 `references`（无命中则 `[]`）
7. 流式 `token`：
   - **正常结束**：写 assistant（无命中写友好提示文案）+ 有命中则写 `chat_references` → `done`
   - **失败或前端停止（Abort）**：**不写** assistant、不写引用；user 已落库保留；失败时推 `error`
8. 前端「停止生成」：`AbortController.abort()`；本地去掉半截助手气泡；刷新后仅见已落库的用户消息

### 4.5 前端（改造现有智能问答页）

- **左**：会话列表（新建 / 选中 / 删除；可就地改名 → `sessions/update`）
- **右**：消息流 + 流式气泡 + 引用；顶部只读展示绑定知识库名称
- **新建**：选知识库 → `sessions/create`（默认 title「新会话」）→ 进入对话
- **提问**：仅 `sessions/ask-stream`；生成中提供「停止」按钮
- **切换/刷新**：`messages/list` 拉历史（含 references）
- 无会话选中时右侧空态引导「新建或选择会话」
- 代码注释保持前端可读的中文说明（与 5A 同风格）
- 页内**不保留**无会话快速提问入口；无会话接口仅后端保留

### 4.6 与旧接口的关系

| 接口 | 定位 |
|------|------|
| `/chat/ask` | 无会话、完整 JSON；联调/脚本 |
| `/chat/ask-stream` | 无会话流式（5A） |
| `/chat/sessions/ask-stream` | 产品主路径（5B） |

### 4.7 5B 验收

- [ ] 创建 / 列表 / 详情 / 改名 / 删除会话正常
- [ ] 同会话追问能利用最近 10 条历史理解指代
- [ ] 刷新后历史与引用仍在；无命中时 user+assistant 提示均落库
- [ ] 停止或失败不产生半截 assistant 记录
- [ ] 自动 title 与手动改名互不误伤（仅默认「新会话」可被首问覆盖）
- [ ] ORM + API 单测（Mock LLM/Embedding/Milvus）

---

## 5. 实施顺序与产出

1. ~~写 5A 实现计划 → 实现流式 → 联调前端~~（已完成）
2. 写 5B 实现计划 → ORM/Service/API → 改造 ChatPage
3. 更新 `AGENTS.md` 约定（会话接口、`CHAT_HISTORY_MAX_CHARS`、停止策略）

## 6. 非目标（本阶段仍不做）

- 登录态 / JWT
- Rerank、HyDE、问题改写
- 评测集自动跑分、点赞反馈
- 会话内换知识库
- `sessions/ask` 非流式
- 上传时强制向量化闸门（可另开小需求）

## 7. 决策记录

| 项 | 结论 |
|----|------|
| 分期 | 先 5A 流式 → 再 5B 多轮 |
| 实现路径 | 方案 A：扩展现有 chat 域 + 改造 ChatPage |
| 前端布局 | 左会话列表 + 右聊天 |
| 知识库 | 创建时绑定，会话内不可改 |
| 历史条数 | 最近 **10** 条消息 |
| 历史字符上限 | `CHAT_HISTORY_MAX_CHARS=4000`（与检索限额分开） |
| 无命中落库 | user + assistant（友好提示）都落 |
| title | 默认「新会话」；首问自动截断覆盖；支持手动 update |
| token_count | `len(content)` |
| 停止生成 | 要做；中断后不落 assistant |
| 会话提问 | **仅** `sessions/ask-stream` |
| `/chat/ask` | **保留**作无会话非流式兜底 |
| 删除 | DB CASCADE |
| 产品默认路径 | 5B 后以会话流式为主；页内无会话入口取消 |

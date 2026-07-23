# 第 3 阶段实现计划：文档解析与切片（方案 A）

> **For agentic workers:** 按 Task 顺序实现；每完成一个 Task 勾选 checkbox。优先单 Task 单 PR 或同一分支内按序提交。

**Goal:** 上传文档后经 Celery 异步完成解析与切片，chunks 落 PostgreSQL，文档状态到达 `chunked`；前端可轮询状态。不做 Embedding / Milvus。

**Architecture:** 沿用 `route → schema → service → model`；耗时链路放入 Celery Worker。解析与切片无状态纯函数，由 `process_document` 编排并写库。

**Tech Stack:** FastAPI, SQLAlchemy, Celery, Redis, MinIO, pypdf, python-docx, Vue3

**设计依据:** [2026-07-23-document-parse-chunk-design.md](../specs/2026-07-23-document-parse-chunk-design.md)

**终态约定（方案 A）:** 成功 = `chunked`（已切片）；`embedding` / `indexed` 留给第 4 阶段。

---

## Task 拆分总览

| Task | 名称 | 依赖 | 产出 |
|------|------|------|------|
| 1 | 状态枚举 `chunked` + Chunk ORM | 无 | DB/ORM/前端状态文案 |
| 2 | 解析服务 | 无 | `document_parser.py` + 单测 |
| 3 | 切片服务 | 无 | `text_splitter.py` + 单测 |
| 4 | Chunk 写入服务 | Task 1 | `chunk_service` + 清理/落库 |
| 5 | Celery 基建与 `process_document` | Task 2–4 | Worker 可跑通主流程 |
| 6 | 上传投递 + chunks 列表接口 | Task 5 | API 契约与接口测试 |
| 7 | 前端轮询与状态展示 | Task 1, 6 | DocumentPage 体验 |
| 8 | 使用文档与联调验收 | Task 6–7 | `backend/docs` 说明 |

建议并行：Task 2 与 Task 3 可并行；Task 1 需尽早完成供后续依赖。

---

### Task 1: 状态枚举 `chunked` 与 Chunk ORM

**Files:**
- Modify: `backend/scripts/neon-create-knowflow-tables.sql`
- Create: `backend/scripts/neon-alter-document-status-chunked.sql`
- Modify: `backend/app/models/document.py`（注释/校验如有）
- Create/Modify: `backend/app/models/chunk.py`
- Modify: `frontend/src/utils/document-status.js`
- Modify: `AGENTS.md`（补充第 3 阶段状态约定，可选）

- [ ] Neon / 本地枚举新增 `chunked`（`ALTER TYPE ... ADD VALUE 'chunked'`）
- [ ] 实现 `DocumentChunk` ORM，字段与 `document_chunks` 表对齐
- [ ] 前端状态映射补齐：`chunked`（已切片）、`embedding`（向量化中，预留）
- [ ] 更新建表脚本中的 enum 定义，保证新环境直接建库含 `chunked`

**验收:**
- 新库建表含 `chunked`
- 已有库执行 alter 脚本成功
- 前端对 `chunked` 显示「已切片」

---

### Task 2: 文档解析服务

**Files:**
- Modify: `backend/app/services/document_parser.py`
- Create: `backend/tests/test_document_parser.py`
- Fixture: 小型 pdf/docx/txt/md 样例（或用代码生成最小文件）

- [ ] 实现 `parse_document(file_path) -> list[{page_number, content}]`
- [ ] 实现 `parse_pdf` / `parse_docx` / `parse_text`（txt+md）
- [ ] 不支持类型抛明确异常（含 xlsx）
- [ ] 单测覆盖各格式与不支持类型

**验收:**
- PDF 多页返回带页码；DOCX/TXT/MD 返回文本
- 不支持类型断言失败信息可读

---

### Task 3: 文本切片服务

**Files:**
- Modify: `backend/app/services/text_splitter.py`
- Create: `backend/tests/test_text_splitter.py`

- [ ] 实现 `split_text(pages, chunk_size=800, chunk_overlap=120)`
- [ ] 保留 `page_number`；生成有序 `chunk_index`（可由上层赋值）
- [ ] 空页跳过；全空结果由上层判失败
- [ ] 单测：短文本、跨 overlap、多页

**验收:**
- 固定输入切片数量与 overlap 行为符合预期

---

### Task 4: Chunk 写入与清理

**Files:**
- Create: `backend/app/services/chunk_service.py`
- Modify: `backend/app/services/token_service.py`（或内联简单估算）
- Create: `backend/tests/test_chunk_service.py`

- [ ] `replace_document_chunks(db, document, chunks)`：删旧写新，事务内完成
- [ ] 计算 `content_hash`、`token_count`
- [ ] 更新 `documents.chunk_count`
- [ ] `list_chunks(document_id, page, page_size)` 分页查询

**验收:**
- 重复写入同一文档不会产生重复 `chunk_index`
- `chunk_count` 与库中条数一致

---

### Task 5: Celery 与 `process_document`

**Files:**
- Modify: `backend/app/tasks/celery_app.py`
- Modify: `backend/app/tasks/document_tasks.py`
- Modify: `backend/app/services/object_storage.py`（如需下载到临时文件）
- Modify: `docker-compose.yml` / README（Worker 启动说明，可选）
- Create: `backend/tests/test_process_document_task.py`（可用同步调用任务函数 + FakeStorage）

- [ ] 配置 Celery broker/backend 与 `documents` 队列
- [ ] 实现 `process_document(document_id)`：
  1. `parsing` → 下载 → 解析
  2. `chunking` → 切片
  3. 写 chunks → `chunked`
  4. 异常 → `failed` + `error_message`
- [ ] 临时文件用后清理
- [ ] 文档说明 Worker 启动命令

**验收:**
- 在测试中调用任务函数后，文档为 `chunked` 且有 chunks
- 解析失败文档为 `failed`

**Worker 启动（文档写入 README/usage）:**

```bash
cd backend
celery -A app.tasks.celery_app.celery_app worker -Q documents --loglevel=info
```

---

### Task 6: 上传投递任务 + Chunks 列表 API

**Files:**
- Modify: `backend/app/api/v1/documents.py`
- Modify: `backend/app/schemas/document.py`
- Modify: `backend/app/services/document_service.py`
- Modify: `backend/tests/test_documents_api.py`
- Create: `backend/tests/test_document_chunks_api.py`（或并入现有测试）

- [ ] `create` 成功后 `process_document.delay(document_id)`（测试可 mock delay）
- [ ] 响应可选带 `task_id`
- [ ] 新增 `GET /api/v1/documents/chunks?document_id=&page=&page_size=`
- [ ] 统一响应格式；文档不存在返回错误码

**验收:**
- 接口测试：create 触发 delay 一次
- chunks 列表分页正确；无权限/不存在文档行为符合约定

---

### Task 7: 前端轮询与状态展示

**Files:**
- Modify: `frontend/src/utils/document-status.js`
- Modify: `frontend/src/views/DocumentPage.vue`
- Modify: `frontend/src/components/DocumentDetailDrawer.vue`（展示 chunk_count / error）
- Modify: `frontend/src/services/document-service.js`（如有 chunks API）
- Optional: 详情内简易 chunk 预览列表

- [ ] 列表存在非终态（`uploaded|parsing|chunking`）时轮询 list/detail
- [ ] 到达 `chunked` 或 `failed` 停止轮询
- [ ] 失败展示 `error_message`
- [ ] `chunk_count` 在表格或详情可见

**验收:**
- 手动联调：上传 PDF 可见状态推进到「已切片」
- 失败文件显示失败 Tag 与原因

**终态集合（前端）:**

```text
终态：chunked | failed | indexed
进行中：uploaded | parsing | chunking | embedding
```

> 本阶段实际只会到 `chunked` / `failed`；`embedding`/`indexed` 预留。

---

### Task 8: 使用文档与联调清单

**Files:**
- Create/Update: `backend/docs/document-parse-chunk-phase3-usage.md`
- Modify: `AGENTS.md`（第 3 阶段接口与状态约定）
- Optional: `README.md` 增加 Worker 启动一节

- [ ] 写清状态机、接口、Worker 启动、联调步骤、与第 4 阶段边界
- [ ] 提供 curl / 前端操作验收清单

**验收:**
- 按文档可从零启动 API + Worker + 前端完成一次 PDF 切片联调

---

## 建议提交顺序

```text
1) Task 1  DB/ORM/前端状态
2) Task 2 + Task 3  解析与切片（可两个 commit）
3) Task 4  chunk 落库
4) Task 5  Celery 任务
5) Task 6  API 投递与 chunks 列表
6) Task 7  前端轮询
7) Task 8  文档收尾
```

## 风险与注意

1. **Neon 枚举变更**：`ADD VALUE` 需单独事务；已有环境必须跑 alter 脚本。
2. **Worker 未启动**：文档会停在 `uploaded`，需在文档中写明排查。
3. **SQLite 测试 vs Postgres 枚举**：单测可用字符串 status；集成以 Neon/Postgres 为准。
4. **与第 4 阶段边界**：禁止在本阶段写 Milvus 或把成功标成 `indexed`。

## 完成定义（DoD）

- [ ] 方案 A 状态机跑通至 `chunked`
- [ ] PDF/DOCX/TXT/MD 均可切片落库
- [ ] 相关单测/接口测通过
- [ ] 使用文档可独立联调
- [ ] PR 描述写明「不含 Embedding/Milvus」

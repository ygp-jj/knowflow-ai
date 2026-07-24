# 第 3 阶段设计：文档解析与切片（方案 A）

## 1. 背景与目标

第 2 阶段已完成知识库 CRUD 与文档上传（MinIO + `documents` 落库，初始状态 `uploaded`）。

第 3 阶段目标：上传后**异步**完成文档解析与文本切片，将 chunk 写入 PostgreSQL，并驱动文档状态流转；前端可轮询看到状态变化与切片数量。

**本阶段不包含**：Embedding、Milvus 入库、RAG 问答（属第 4 / 5 阶段）。

## 2. 方案选择：方案 A

| 项目 | 约定 |
|------|------|
| 成功终态 | `chunked`（已切片，待向量化） |
| 第 4 阶段起点 | `chunked → embedding → indexed` |
| 硬验收 | `document_chunks` 有记录，且 `documents.chunk_count` 与条数一致 |
| 不提前标 `indexed` | 避免「已入库」但实际无向量的语义混淆 |

### 状态机（本阶段）

```text
uploaded → parsing → chunking → chunked
                              ↘ failed
```

完整生命周期（含后续阶段）：

```text
uploaded → parsing → chunking → chunked → embedding → indexed
                 ↘ failed ↙              ↘ failed ↙
```

> 说明：现有 `document_status_enum` 无 `chunked`，本阶段需新增枚举值，并同步 ORM / 前端状态映射。

## 3. 范围

### 3.1 必做

1. Celery + Redis 异步任务基建
2. 从 MinIO 下载文件到可解析输入
3. 文档解析：PDF / DOCX / TXT / Markdown
4. 文本切片：`chunk_size=800`，`chunk_overlap=120`（字符级）
5. `document_chunks` 落库与 `chunk_count` 更新
6. 上传成功后投递 `process_document` 任务
7. 前端状态轮询 + `chunked` / `failed` 展示
8. 可选但推荐：按文档查询 chunk 列表接口（联调验收）

### 3.2 明确不做

- Embedding / Milvus / TopK
- 流式问答与引用来源
- 按标题 / Token 的进阶切片
- xlsx 解析（上传可存，本阶段解析报「暂不支持」并置 `failed`）

## 4. 数据模型

### 4.1 documents.status

新增：`chunked`

前端文案建议：

| status | 文案 | 颜色建议 |
|--------|------|----------|
| uploaded | 待解析 | processing |
| parsing | 解析中 | warning |
| chunking | 切片中 | geekblue |
| chunked | 已切片 | cyan |
| embedding | 向量化中 | purple |
| indexed | 已入库 | success |
| failed | 失败 | error |

### 4.2 document_chunks

沿用已有建表字段：

```text
id
document_id
knowledge_base_id
chunk_index
content
content_hash
page_number
token_count
vector_id          -- 本阶段保持 NULL
metadata           -- 本阶段可空或仅存基础信息
created_at
```

约束：

- `(document_id, chunk_index)` 唯一
- 删除文档时级联删除 chunks（已有 FK ON DELETE CASCADE）
- 任务重跑：先删该文档旧 chunks，再写入新 chunks

## 5. 核心流程

```text
前端上传文件
  ↓
POST /api/v1/documents/create
  ↓
校验知识库 → 上传 MinIO → 写 documents(status=uploaded)
  ↓
投递 Celery: process_document(document_id)
  ↓
立即返回 { document, task_id? }
  ↓
Worker:
  1. status = parsing
  2. MinIO 下载 → parse_document
  3. status = chunking
  4. split_text → 写 document_chunks
  5. 更新 chunk_count，status = chunked
  失败则 status = failed，写 error_message
  ↓
前端轮询 detail/list，直至 chunked 或 failed
```

## 6. 模块划分

| 模块 | 路径 | 职责 |
|------|------|------|
| Celery App | `backend/app/tasks/celery_app.py` | broker/backend、队列路由 |
| 文档任务 | `backend/app/tasks/document_tasks.py` | `process_document` 状态机编排 |
| 解析服务 | `backend/app/services/document_parser.py` | PDF/DOCX/TXT/MD → pages |
| 切片服务 | `backend/app/services/text_splitter.py` | pages → chunks |
| Chunk 模型 | `backend/app/models/chunk.py` | ORM |
| Chunk 服务 | `backend/app/services/chunk_service.py`（建议新增） | 清理/批量写入/列表查询 |
| Token 估算 | `backend/app/services/token_service.py` | 写 `token_count`（可用字符近似或 tiktoken） |
| 对象存储 | `backend/app/services/object_storage.py` | 补充下载到临时文件（若需要） |
| 文档接口 | `backend/app/api/v1/documents.py` | 创建后投递任务；可选 chunks 列表 |
| 前端状态 | `frontend/src/utils/document-status.js` | 补 `chunked`/`embedding` |
| 前端轮询 | `frontend/src/views/DocumentPage.vue` | 列表/详情轮询 |

## 7. 接口约定（延续现有风格）

路径不写动态 ID 段，统一响应 `{ code, message, data }`。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/documents/create` | 上传后投递任务；`data` 含文档信息，可选 `task_id` |
| GET | `/api/v1/documents/detail?id=` | 返回 `status` / `chunk_count` / `error_message` |
| GET | `/api/v1/documents/list?...` | 同上字段，供轮询 |
| GET | `/api/v1/documents/chunks?document_id=&page=&page_size=` | **本阶段新增（推荐）**：分页查看切片 |

### create 响应补充（建议）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 12,
    "knowledge_base_id": 1,
    "file_name": "员工手册.pdf",
    "file_type": "pdf",
    "file_size": 102400,
    "status": "uploaded",
    "error_message": null,
    "chunk_count": 0,
    "task_id": "celery-task-uuid",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### chunks 列表响应（建议）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "document_id": 12,
        "chunk_index": 0,
        "content": "...",
        "page_number": 1,
        "token_count": 210
      }
    ],
    "total": 26,
    "page": 1,
    "page_size": 10
  }
}
```

## 8. 解析与切片规则

### 8.1 解析输出

```python
[
  {"page_number": 1, "content": "..."},
  {"page_number": 2, "content": "..."},
]
```

- PDF：按页提取，`page_number` 从 1 起
- DOCX / TXT / MD：整文一条，`page_number=null`
- 不支持扩展名：置 `failed`，`error_message` 说明原因

### 8.2 切片参数（MVP）

```text
chunk_size = 800
chunk_overlap = 120
```

- 空内容：`failed`，提示「文档无有效文本」
- `content_hash`：对 `content` 做 SHA-256（或前 64 位约定）
- `token_count`：MVP 可用 `len(content)` 近似，或轻量 tiktoken；需在实现中统一一种并文档化

## 9. 错误与重试

| 场景 | 行为 |
|------|------|
| 知识库不存在 | create 返回 404，不投递任务 |
| 不支持文件类型 | 任务内 `failed` |
| 解析异常 / 下载失败 | 任务内 `failed` + error_message |
| 切片结果为空 | 任务内 `failed` |
| 任务重复触发 | 先删旧 chunks 再写，保证幂等 |
| Worker 未启动 | 文档停留 `uploaded`；前端可持续轮询，运维需启动 Worker |

## 10. 验收标准（方案 A）

1. 上传 PDF 后状态依次：`uploaded → parsing → chunking → chunked`
2. PostgreSQL 可见对应 `document_chunks`，`chunk_count` 正确
3. DOCX / TXT / MD 同样可跑通
4. 失败文档为 `failed`，前端可见 `error_message`
5. 前端轮询可看到状态变化，无需整页手动刷新
6. **不要求** Milvus 有向量，**不要求** 状态为 `indexed`

## 11. 与第 4 阶段衔接

第 4 阶段 Worker / 任务应只处理 `status=chunked` 的文档：

```text
chunked → embedding → 写 Milvus + 回填 vector_id → indexed
```

本阶段 `vector_id` 一律为 `NULL`。

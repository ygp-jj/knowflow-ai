# 第 3 阶段：文档解析与切片 — 使用说明（方案 A）

> 设计：[phase3-document-parse-chunk-design.md](./phase3-document-parse-chunk-design.md)  
> 实现计划：[phase3-document-parse-chunk-plan.md](./phase3-document-parse-chunk-plan.md)

## 1. 阶段目标

上传文档后，文件仅保存为 `uploaded`。  
用户在文档列表点击 **「切片」** 后，系统才异步：

1. 解析文件文本（PDF / DOCX / TXT / Markdown）
2. 按固定窗口切片
3. 写入 `document_chunks`
4. 将文档状态更新为 **`chunked`（已切片）**

本阶段**不**做 Embedding、**不**写 Milvus、**不**进入 `embedded`。  
列表页**不轮询**；完成后请手动点「刷新」查看状态。

## 2. 状态机（方案 A）

```text
uploaded → parsing → chunking → chunked   （成功，第 3 阶段结束）
                 ↘ failed ↙

# 第 4 阶段再继续：
chunked → embedding → embedded
```

| 状态 | 含义 | 本阶段是否出现 |
|------|------|----------------|
| uploaded | 已上传，待处理 | 是 |
| parsing | 解析中 | 是 |
| chunking | 切片中 | 是 |
| chunked | 已切片，待向量化 | 是（成功终态） |
| embedding | 向量化中 | 否（第 4 阶段） |
| embedded | 已完成（含向量） | 否（第 4 阶段） |
| failed | 失败 | 是 |

## 3. 依赖与启动

### 3.1 依赖服务

- PostgreSQL（Neon 或本地）
- Redis（Celery broker / result backend）
- MinIO（文档对象）
- FastAPI 后端
- **Celery Worker（必须）**

### 3.2 枚举升级（已有库）

新环境：使用更新后的 `neon-create-knowflow-tables.sql`（含 `chunked`、`embedded`）。

已有 Neon 库若缺少枚举值，在 SQL Editor 或脚本依次执行：

1. `backend/scripts/neon-alter-document-status-chunked.sql`
2. `backend/scripts/neon-alter-document-status-embedded.sql`（新增 `embedded`，并将历史 `indexed` 更新为 `embedded`）

```powershell
cd backend
python scripts\create_neon_tables.py --sql-file scripts\neon-alter-document-status-chunked.sql
python scripts\create_neon_tables.py --sql-file scripts\neon-alter-document-status-embedded.sql
```

若曾执行过旧版建表脚本且枚举无 `chunked`/`embedded`，务必先跑上述 ALTER，再启动 Worker。

### 3.3 启动 Worker

```bash
cd backend
# 确保 .env 中 REDIS / DATABASE / MinIO 配置正确
```

**Windows（PowerShell）推荐：**

```powershell
.\.venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app.celery_app worker -Q documents --pool=solo --loglevel=info
```

> Windows 必须加 `--pool=solo`（或 `threads`）。默认 prefork 会报「拒绝访问 / 句柄无效」。

**Linux / macOS：**

```bash
celery -A app.tasks.celery_app.celery_app worker -Q documents --loglevel=info
```

未启动 Worker 时：点击切片后任务会堆积，文档状态不会推进。

### 3.4 启动 API / 前端

```bash
# 后端
cd backend
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm run dev
```

## 4. 接口说明

统一响应：`{ "code": 0, "message": "success", "data": ... }`，错误时 `data` 为 `null`。

风格与第 2 阶段一致：**URL 路径不写动态 id**。

### 4.1 上传文档（不自动切片）

```http
POST /api/v1/documents/create
Content-Type: multipart/form-data
```

字段：

- `knowledge_base_id`
- `file`

行为：

1. 上传 MinIO
2. 写入 `documents`，`status=uploaded`
3. **不**投递 Celery 任务
4. 立即返回

### 4.1.1 手动触发切片

```http
POST /api/v1/documents/chunk
Content-Type: application/json
```

```json
{ "id": 12 }
```

行为：

1. 校验文档存在且状态允许切片（`uploaded` / `failed` / `chunked`）
2. 投递 Celery 任务 `process_document`
3. 返回 `task_id`（可选）
4. 前端列表不自动轮询；用户点击「刷新」查看 `parsing → chunking → chunked`

### 4.2 查询详情 / 列表（手动刷新）

```http
GET /api/v1/documents/detail?id=12
GET /api/v1/documents/list?page=1&page_size=10&knowledge_base_id=1
```

关注字段：

- `status`
- `chunk_count`
- `error_message`

前端不轮询；用户手动刷新详情/列表，直到看到 `chunked` 或 `failed`。

### 4.3 查询切片列表（推荐）

```http
GET /api/v1/documents/chunks?document_id=12&page=1&page_size=10
```

返回分页：`items` / `total` / `page` / `page_size`。

`items` 元素建议字段：`id`、`document_id`、`chunk_index`、`content`、`page_number`、`token_count`。

本阶段 `vector_id` 均为空，列表可不返回或返回 `null`。

## 5. 解析与切片规则

### 支持格式

| 扩展名 | 解析方式 |
|--------|----------|
| `.pdf` | 按页提取文本 |
| `.docx` | 段落拼接 |
| `.txt` / `.md` | UTF-8 全文 |
| 其他（如 `.xlsx`） | 本阶段不支持，任务失败 |

### 切片参数（MVP）

```text
chunk_size = 256 字符
chunk_overlap = 50 字符
（可用环境变量 CHUNK_SIZE / CHUNK_OVERLAP 覆盖）
```

## 6. 前端行为说明

1. 上传成功后列表出现新文档，状态「待解析」
2. 用户点击「切片」才开始后台解析切片
3. 列表**不轮询**；用户点击「刷新」查看状态与切片数
4. 状态为「失败」时可再次点击「切片」重试
5. 状态为「已切片」时可「重新切片」；详情抽屉可预览 chunk
6. 文档详情抽屉会分页加载切片列表；列表「切片」按钮在可查看时可用

## 7. 联调验收清单

- [ ] Redis、MinIO、Postgres 可连
- [ ] API 与 Celery Worker 均已启动
- [ ] 上传 PDF：`uploaded → parsing → chunking → chunked`
- [ ] `document_chunks` 有数据，`chunk_count` 一致
- [ ] 上传 TXT/MD/DOCX 同样成功
- [ ] 上传不支持类型 → `failed` + 明确错误信息
- [ ] 前端无需整页刷新即可看到状态变化
- [ ] 确认成功文档**不是** `embedded`（方案 A；本阶段终态为 `chunked`）

### curl 示例

```bash
# 上传（按实际文件路径替换）
curl -X POST "http://127.0.0.1:8000/api/v1/documents/create" \
  -F "knowledge_base_id=1" \
  -F "file=@./sample.pdf"

# 刷新详情（手动）
curl "http://127.0.0.1:8000/api/v1/documents/detail?id=12"

# 查看切片
curl "http://127.0.0.1:8000/api/v1/documents/chunks?document_id=12&page=1&page_size=10"
```

## 8. 常见问题

### 一直停在 uploaded

- Worker 是否启动？
- Redis 地址是否与 `.env` 一致？
- 任务是否投递到 `documents` 队列？

### 状态变为 failed

- 查看 `error_message`
- 常见原因：文件类型不支持、PDF 无文本层、MinIO 下载失败、空文本

### 与第 2 阶段文档管理文档关系

- 上传 / 下载 / 删改仍见：`document-management-api-usage.md`
- 本文件只补充「上传之后的异步解析切片」链路

## 9. 和第 4 阶段的边界

| 能力 | 第 3 阶段 | 第 4 阶段 |
|------|-----------|-----------|
| 解析 + 切片 | ✅ | — |
| `document_chunks` 文本 | ✅ | — |
| Embedding | ❌ | ✅ |
| Milvus / `vector_id` | ❌ | ✅ |
| 状态 `embedded` | ❌ | ✅ |

第 4 阶段应从 `status=chunked` 的文档继续处理。

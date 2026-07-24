# KnowFlow AI 后端接口架构说明

> 本文档面向前端开发者，介绍后端接口的分层架构、请求流转方式、接口速查表，以及错误排查和新增接口指南。

---

## 一、整体分层架构

```
前端 HTTP 请求
       ▼
┌─────────────────────────────────────────────────────┐
│  main.py（应用入口）                                  │
│  - 创建 FastAPI 实例                                 │
│  - 配置 CORS 中间件                                  │
│  - 注册各模块 Router（prefix 决定 URL 前缀）           │
└──────────────────────────┬──────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────┐
│  Router 路由层  (app/api/v1/*.py)                     │
│  - 定义 HTTP 端点（GET/POST/PUT/DELETE）              │
│  - 接收并校验请求参数（Query / Form / Body）           │
│  - 通过 Depends(get_db) 注入数据库会话                │
│  - 调用 Service 层                                   │
│  - 使用 Schema 序列化响应 → 返回统一格式               │
└──────────────────────────┬──────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────┐
│  Schema 校验层  (app/schemas/*.py)                    │
│  - Pydantic BaseModel 定义请求体字段约束              │
│  - 自动进行类型/长度/范围校验                          │
│  - 提供 model_validate() 将 ORM 对象序列化为响应数据   │
└──────────────────────────┬──────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────┐
│  Service 业务层  (app/services/*.py)                  │
│  - 纯业务逻辑（创建/更新/删除/下载/上传 MinIO）       │
│  - 执行数据库 CRUD 操作                              │
│  - 执行业务规则判断（所有权验证、关联检查等）           │
└──────────────────────────┬──────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────┐
│  Model 数据层  (app/models/*.py)                      │
│  - SQLAlchemy ORM 模型，对应数据库表                  │
│  - 通过 Base 基类继承，定义字段和关系                  │
└──────────────────────────┬──────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────┐
│  Database 底层  (app/core/database.py)                │
│  - SQLAlchemy Engine 管理连接池（pool_size=10）       │
│  - SessionLocal 会话工厂                             │
│  - get_db() 生成器为每个请求提供独立会话               │
└─────────────────────────────────────────────────────┘
```

---

## 二、统一响应格式

所有接口返回同一结构，前端只需判断 `code === 0` 即为成功：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

错误时：

```json
{
  "code": 404,
  "message": "知识库不存在",
  "data": null
}
```

构造函数位于 `app/schemas/common.py`：
- `success_response(data)` — 包装成功响应
- `error_response(code, message)` — 包装业务错误响应

---

## 三、完整请求流程示例

### 示例 1：创建知识库 `POST /api/v1/knowledge-bases/create`

| 步骤 | 层级 | 文件 | 做了什么 |
|------|------|------|----------|
| 1 | 入口 | `main.py` | 路由注册，绑定 prefix `/api/v1/knowledge-bases` |
| 2 | Router | `app/api/v1/knowledge_bases.py` | `@router.post("/create")` 接收请求体 `KnowledgeBaseCreate`，注入 db 会话 |
| 3 | Schema | `app/schemas/knowledge_base.py` | 自动校验：name(1-200字符)、owner_id(>0) |
| 4 | Service | `app/services/knowledge_base_service.py` | 创建 ORM 对象 → `db.add()` → `db.commit()` → `db.refresh()` |
| 5 | Model | `app/models/knowledge_base.py` | ORM 映射到 `knowledge_bases` 表，执行 INSERT |
| 6 | 响应 | Router | `KnowledgeBaseRead.model_validate(kb)` 序列化 → `success_response(data)` 包装 |

前端收到：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "产品文档库",
    "description": "存放产品手册",
    "owner_id": 1,
    "created_at": "2026-07-17T10:00:00Z",
    "updated_at": "2026-07-17T10:00:00Z"
  }
}
```

### 示例 2：上传文档 `POST /api/v1/documents/create`

| 步骤 | 层级 | 文件 | 做了什么 |
|------|------|------|----------|
| 1 | Router | `app/api/v1/documents.py` | 接收 `multipart/form-data`：`knowledge_base_id` + `file` |
| 2 | Service | `app/services/document_service.py` | 验证知识库存在 → 构造 MinIO 路径 → 上传文件 → 写数据库 |
| 3 | 存储 | MinIO | 文件存到 `knowledge-bases/{kb_id}/{timestamp}-{uuid}.ext` |
| 4 | Model | `app/models/document.py` | INSERT documents 表（元数据+状态） |
| 5 | 响应 | Router | 返回 DocumentRead 包含文件大小、状态等 |

---

## 四、前端接口调用速查表

| 功能 | 方法 | URL | 参数位置 | 参数说明 |
|------|------|-----|----------|----------|
| 创建知识库 | POST | `/api/v1/knowledge-bases/create` | Body JSON | `{name, description?, owner_id}` |
| 知识库列表 | GET | `/api/v1/knowledge-bases/list` | Query | `owner_id, page, page_size` |
| 知识库详情 | GET | `/api/v1/knowledge-bases/detail` | Query | `id, owner_id` |
| 更新知识库 | PUT | `/api/v1/knowledge-bases/update` | Body JSON | `{id, name, description?, owner_id}` |
| 删除知识库 | DELETE | `/api/v1/knowledge-bases/delete` | Query | `id, owner_id` |
| 上传文档 | POST | `/api/v1/documents/create` | Form-Data | `knowledge_base_id, file` |
| 文档列表 | GET | `/api/v1/documents/list` | Query | `page, page_size, knowledge_base_id?` |
| 文档详情 | GET | `/api/v1/documents/detail` | Query | `id` |
| 更新文档名 | PUT | `/api/v1/documents/update` | Body JSON | `{id, file_name}` |
| 删除文档 | DELETE | `/api/v1/documents/delete` | Query | `id` |
| 下载文档 | GET | `/api/v1/documents/download` | Query | `id`（返回文件流） |
| 健康检查 | GET | `/health` | 无 | 返回 `{status, app}` |

---

## 五、关键设计约定（前端需注意）

1. **ID 不在 URL 路径中** — 详情和删除通过 Query 参数 `?id=xxx` 传入，更新通过 Body 传入
2. **owner_id 前端显式传入** — 当前阶段无登录态，前端负责携带用户标识
3. **分页返回固定结构** — `{ items: [...], total, page, page_size }`
4. **文件上传用 Form-Data** — 不是 JSON，字段为 `knowledge_base_id` 和 `file`
5. **下载接口返回文件流** — 不暴露 MinIO 真实地址，通过后端代理返回
6. **删除知识库有前置检查** — 如果知识库下有文档会返回 `code: 400`

---

## 六、错误排查指南

### 6.1 常见错误及排查步骤

| 现象 | 可能原因 | 排查方法 |
|------|----------|----------|
| 前端收到 CORS 错误 | 前端地址未加入允许列表 | 检查 `backend/.env` 中 `CORS_ORIGINS` 是否包含前端地址 |
| 返回 422 Unprocessable Entity | 请求参数格式不对 | 查看响应体中的 `detail` 字段，会精确标注哪个字段校验失败 |
| 返回 `{"code": 404, ...}` | 资源不存在或 owner_id 不匹配 | 确认传入的 id 和 owner_id 是否正确 |
| 返回 `{"code": 400, ...}` | 业务规则不满足（如删除有文档的知识库） | 阅读 message 字段的提示信息 |
| 返回 500 Internal Server Error | 后端代码异常 | 查看后端终端日志，定位 traceback |
| 文件上传失败 | MinIO 服务未启动或配置错误 | 检查 Docker 中 MinIO 容器状态，确认 `.env` 中 `MINIO_*` 配置 |
| 数据库连接失败 | PostgreSQL 连接串错误或服务不可达 | 检查 `.env` 中 `DATABASE_URL`，用数据库客户端测试连通性 |

### 6.2 排查工具

1. **Swagger 文档** — 启动后端后访问 `http://localhost:8000/docs`，可在线测试所有接口
2. **后端终端日志** — FastAPI 在 debug 模式下会打印完整的请求和错误堆栈
3. **健康检查** — 先调用 `GET /health` 确认后端服务是否存活
4. **422 响应详情** — FastAPI 的参数校验错误会返回详细的 JSON 结构：

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    }
  ]
}
```

### 6.3 修改已有接口的步骤

假设要给「知识库列表」接口增加一个可选的 `keyword` 搜索参数：

1. **Router 层** — 在 `app/api/v1/knowledge_bases.py` 的 `list_items` 函数签名中增加参数：
   ```python
   keyword: str | None = Query(default=None, description="搜索关键词")
   ```

2. **Service 层** — 在 `app/services/knowledge_base_service.py` 的 `list_knowledge_bases` 中增加过滤逻辑：
   ```python
   if keyword:
       query = query.filter(KnowledgeBase.name.ilike(f"%{keyword}%"))
   ```

3. **测试** — 在 Swagger 文档中或用 curl 测试新参数是否生效

4. **通知前端** — 更新本文档的速查表

---

## 七、新增接口指南

以新增一个「标签管理」模块为例，需要按以下步骤逐层创建：

### 步骤 1：创建 Model（数据层）

新建 `app/models/tag.py`：

```python
"""标签 ORM 模型定义。"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Tag(Base):
    """标签 ORM 模型，对应 tags 表。"""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

### 步骤 2：创建 Schema（校验层）

新建 `app/schemas/tag.py`：

```python
"""标签请求与响应 Schema。"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TagCreate(BaseModel):
    """创建标签请求。"""
    name: str = Field(..., min_length=1, max_length=100, description="标签名称")


class TagRead(BaseModel):
    """标签响应数据。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
```

### 步骤 3：创建 Service（业务层）

新建 `app/services/tag_service.py`：

```python
"""标签管理业务服务。"""

from sqlalchemy.orm import Session
from app.models.tag import Tag
from app.schemas.tag import TagCreate


def create_tag(db: Session, payload: TagCreate) -> Tag:
    """创建标签。"""
    tag = Tag(name=payload.name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def list_tags(db: Session, page: int, page_size: int) -> tuple[list[Tag], int]:
    """分页查询标签。"""
    query = db.query(Tag)
    total = query.count()
    items = query.order_by(Tag.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total
```

### 步骤 4：创建 Router（路由层）

新建 `app/api/v1/tags.py`：

```python
"""标签管理 HTTP 路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import success_response
from app.schemas.tag import TagCreate, TagRead
from app.services.tag_service import create_tag, list_tags

router = APIRouter()


@router.post("/create")
def create(payload: TagCreate, db: Session = Depends(get_db)):
    """创建标签。"""
    tag = create_tag(db, payload)
    data = TagRead.model_validate(tag)
    return success_response(data)


@router.get("/list")
def list_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """分页查询标签列表。"""
    items, total = list_tags(db, page, page_size)
    data = {
        "items": [TagRead.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return success_response(data)
```

### 步骤 5：注册到 main.py

在 `app/main.py` 中添加：

```python
from app.api.v1 import tags

app.include_router(
    tags.router,
    prefix="/api/v1/tags",
    tags=["Tags"]
)
```

### 步骤 6：创建数据库表

在 Neon 数据库中执行对应的 CREATE TABLE SQL，或通过 Alembic 迁移生成。

### 新增接口 Checklist

- [ ] `app/models/` 中创建 ORM 模型
- [ ] `app/schemas/` 中创建请求和响应 Schema
- [ ] `app/services/` 中创建业务逻辑函数
- [ ] `app/api/v1/` 中创建路由文件
- [ ] `app/main.py` 中注册路由（include_router）
- [ ] 数据库中创建对应的表
- [ ] 在 Swagger (`/docs`) 中测试接口
- [ ] 更新本文档的速查表

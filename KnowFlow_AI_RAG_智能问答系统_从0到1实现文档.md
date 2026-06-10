# KnowFlow AI 企业知识库 RAG 智能问答系统：从 0 到 1 实现文档

> 适用人群：前端开发转 AI 应用全栈工程师
> 推荐主线：Vue3 + TypeScript + FastAPI + PostgreSQL(线上PostgreSQL (Neon)(https://neon.com/)) + Redis + Celery + Milvus + LangChain
> 项目目标：完成一个可用于简历、面试演示、GitHub 作品集的企业级 RAG 智能问答系统。

---

## 0. 技术栈纠正说明

你原始设想中写了：

```text
Vue3 + TS + Next.js + AntDesign + Pinia
```

这里需要纠正一点：

**Next.js 是 React 生态的 SSR / 全栈框架，不适合直接和 Vue3 搭配。**

Vue3 项目通常选择：

```text
Vue3 + TypeScript + Vite
```

如果你未来需要 Vue 的 SSR / 全栈能力，可以选择：

```text
Vue3 + Nuxt
```

本项目文档采用下面这套技术栈：

```text
前端：
Vue3 + TypeScript + Vite + Ant Design Vue + Pinia + Vue Router + Axios / Fetch + SSE

后端：
Python + FastAPI + SQLAlchemy + PostgreSQL + Redis + Celery + LangChain + Milvus + Docker Compose

AI 能力：
OpenAI-compatible API
通义 / 智谱 / DeepSeek / 火山 / Moonshot 等国内模型 API
Embedding 模型
RAG 检索
Prompt 模板
简单 Rerank
Token 统计
问答效果评估
```

---

# 1. 项目总览

## 1.1 项目名称

**KnowFlow AI：企业知识库 RAG 智能问答系统**

## 1.2 项目定位

KnowFlow AI 是一个面向企业内部文档的知识库问答系统。

用户可以上传 PDF、Word、Markdown、TXT 等文档，系统自动完成文档解析、文本切片、Embedding 向量化、向量入库。用户提问后，系统会从知识库中检索相关片段，将片段拼接到 Prompt 中调用大模型，并以流式方式返回答案，同时展示引用来源。

## 1.3 MVP 必须完成的闭环

MVP 阶段必须跑通下面这条主链路：

```text
用户上传文档
  ↓
后端解析文档
  ↓
文本切片
  ↓
生成 Embedding
  ↓
存入向量库
  ↓
用户提问
  ↓
检索相关片段
  ↓
拼接 Prompt
  ↓
调用大模型
  ↓
前端流式展示回答
  ↓
展示引用来源
```

## 1.4 最终你要展示给面试官的能力

这个项目不是一个普通聊天框，而是要体现你具备：

- 前端工程能力
- 后端 API 能力
- 文件上传与异步任务处理能力
- RAG 系统理解能力
- 大模型 API 接入能力
- 向量数据库使用能力
- Prompt 设计能力
- 流式响应交互能力
- AI 应用可观测和效果评估意识
- 从 0 到 1 完整交付 AI 应用的能力

---

# 2. 软件、框架与组件说明

## 2.1 前端技术说明

### Vue3

Vue3 是前端框架，负责构建页面、组件和用户交互。

本项目中 Vue3 负责：

- 登录页
- 知识库管理页
- 文档上传页
- 聊天问答页
- 引用来源展示
- 系统配置页
- 数据面板页

### TypeScript

TypeScript 是 JavaScript 的类型增强版本。

本项目中 TypeScript 负责：

- 约束接口返回结构
- 约束组件 Props
- 约束 Pinia 状态
- 减少前后端联调错误
- 提升代码可维护性

### Vite

Vite 是前端构建工具。

它负责：

- 创建 Vue3 项目
- 启动本地开发服务器
- 打包生产环境代码
- 支持快速热更新

### Ant Design Vue

Ant Design Vue 是基于 Vue 的企业级 UI 组件库。

本项目中用它快速实现：

- 表格
- 表单
- 按钮
- 上传组件
- 弹窗
- 抽屉
- 菜单
- 布局
- 标签
- 进度条

### Pinia

Pinia 是 Vue 官方推荐的状态管理工具。

本项目中 Pinia 负责：

- 保存用户登录信息
- 保存 Token
- 保存当前知识库
- 保存模型配置
- 保存聊天状态
- 管理全局 loading / error 状态

### Vue Router

Vue Router 负责前端页面路由。

本项目中页面包括：

```text
/login
/dashboard
/knowledge-bases
/knowledge-bases/:id/documents
/chat/:knowledgeBaseId
/settings/models
/settings/prompts
/evaluations
```

### SSE

SSE，全称 Server-Sent Events，是一种服务端向浏览器持续推送文本数据的方式。

本项目用 SSE 实现大模型回答的流式输出：

```text
用户提问 → 后端调用大模型 → 大模型边生成边返回 → 前端边接收边显示
```

---

## 2.2 后端技术说明

### FastAPI

FastAPI 是 Python Web 框架，用来开发后端 API。

本项目中 FastAPI 负责：

- 用户登录
- 文件上传
- 文档管理
- 知识库管理
- 聊天问答接口
- 流式响应接口
- Prompt 配置接口
- 模型配置接口
- 评估统计接口

### SQLAlchemy

SQLAlchemy 是 Python ORM 框架，用来操作关系型数据库。

本项目中 SQLAlchemy 负责：

- 定义数据表模型
- 操作 PostgreSQL
- 处理用户、文档、知识库、聊天记录等业务数据

### PostgreSQL

PostgreSQL 是关系型数据库。

本项目中 PostgreSQL 负责存储：

- 用户信息
- 知识库信息
- 文档元数据
- 文档切片元数据
- 聊天会话
- 聊天消息
- 引用来源
- 用户反馈
- 模型配置
- Prompt 模板
- Token 统计
- 评估记录

### Redis

Redis 是内存数据库。

本项目中 Redis 负责：

- Celery 消息队列 Broker
- 异步任务状态缓存
- 临时会话缓存
- 限流计数
- 热点配置缓存

### Celery

Celery 是 Python 异步任务队列。

本项目中 Celery 负责处理耗时任务：

- 文档解析
- 文本切片
- Embedding 生成
- 向量入库
- 批量评测
- 报告生成

为什么需要 Celery？

因为文档解析和向量化可能耗时几十秒，如果直接在 HTTP 请求中处理，用户会一直等待，接口容易超时。

正确流程是：

```text
前端上传文档
  ↓
FastAPI 创建文档记录
  ↓
FastAPI 投递 Celery 异步任务
  ↓
立即返回 task_id / document_id
  ↓
前端轮询文档状态
  ↓
Celery 后台完成解析、切片、向量化
  ↓
前端展示完成状态
```

### LangChain

LangChain 是大模型应用开发框架。

本项目中 LangChain 可用于：

- 封装 LLM 调用
- 封装 Embedding 模型
- 对接 Milvus 向量库
- 构建 RAG 检索链
- 管理 Prompt 模板
- 后续扩展 Agent / Tool Calling

### Milvus

Milvus 是向量数据库。

本项目中 Milvus 负责：

- 存储文档切片向量
- 根据用户问题做语义检索
- 返回 TopK 相似片段
- 支撑 RAG 检索

### Docker Compose

Docker Compose 用来一键启动多个服务。

本项目中用 Docker Compose 启动：

- PostgreSQL
- Redis
- Milvus
- 后端 FastAPI
- Celery Worker
- 前端开发服务或生产服务

---

# 3. 系统架构设计

## 3.1 总体架构

```text
┌────────────────────────────────────────────┐
│                前端 Vue3 应用              │
│  登录 / 知识库 / 文档上传 / 聊天 / 评测面板  │
└─────────────────────┬──────────────────────┘
                      │ HTTP / SSE
                      ↓
┌────────────────────────────────────────────┐
│              FastAPI 后端服务              │
│ 用户、知识库、文档、问答、模型、Prompt API   │
└───────────────┬───────────────┬────────────┘
                │               │
                │               │ 投递异步任务
                │               ↓
                │        ┌─────────────────┐
                │        │  Celery Worker  │
                │        │ 文档解析/切片/向量化 │
                │        └────────┬────────┘
                │                 │
                ↓                 ↓
        ┌──────────────┐   ┌──────────────┐
        │ PostgreSQL   │   │   Milvus     │
        │ 业务数据      │   │ 向量数据      │
        └──────────────┘   └──────────────┘
                ↑
                │
        ┌──────────────┐
        │    Redis     │
        │ 队列/缓存     │
        └──────────────┘
                │
                ↓
┌────────────────────────────────────────────┐
│             大模型与 Embedding API          │
│ OpenAI-compatible / 通义 / 智谱 / DeepSeek等 │
└────────────────────────────────────────────┘
```

## 3.2 数据流：文档上传入库

```text
1. 用户选择知识库
2. 用户上传文件
3. 前端调用 POST /api/documents/upload
4. 后端保存文件到本地或对象存储
5. PostgreSQL 创建 document 记录，状态为 uploaded
6. 后端投递 Celery 任务 process_document
7. Celery 读取文件
8. Celery 解析文本
9. Celery 切分文本 chunk
10. Celery 调用 Embedding API
11. Celery 将向量写入 Milvus
12. Celery 将 chunk 元数据写入 PostgreSQL
13. document 状态更新为 indexed
14. 前端显示文档处理完成
```

## 3.3 数据流：用户提问

```text
1. 用户在聊天框输入问题
2. 前端调用 POST /api/chat/stream
3. 后端将问题转成 query embedding
4. 后端去 Milvus 检索 TopK 文档片段
5. 后端根据 chunk_id 查 PostgreSQL 获取原文、文档名、页码
6. 后端构造 Prompt
7. 后端调用大模型 API
8. 大模型流式返回 token
9. FastAPI 通过 SSE 推送给前端
10. 前端逐字展示回答
11. 回答完成后保存聊天记录
12. 前端展示引用来源
```

---

# 4. 本地开发环境安装

## 4.1 必装软件

建议本地安装：

```text
Node.js 20+
pnpm 9+
Python 3.11+
Docker Desktop
Git
**VS** Code
Postman / Apifox
```

可选安装：

```text
DBeaver / DataGrip：查看 PostgreSQL
RedisInsight：查看 Redis
```

## 4.2 检查 Node.js

```bash
node -v
npm -v
```

建议使用 Node.js 20 或更高版本。

安装 pnpm：

```bash
npm install -g pnpm
pnpm -v
```

## 4.3 检查 Python

```bash
python --version
pip --version
```

建议使用 Python 3.11。

推荐安装 uv 或 poetry 管理 Python 依赖。本项目使用pyenv-win管理python版本，
常见命令行：
1.安装某个版本（例如 3.12.0）	pyenv install 3.12.0
2.查看已安装的版本	pyenv versions
3.在当前目录下切换版本（项目级）	pyenv local 3.11.9
4.查看当前激活的版本	pyenv version
5.激活包   .\.venv\Scripts\Activate.ps1，先激活再pip install <真实包名>
6.退出激活  deactivate


简单起步可以先用 venv：

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

## 4.4 安装 Docker Desktop

安装 Docker Desktop 后检查：

```bash
docker -v
docker compose version
```

如果能看到版本号，说明 Docker 和 Compose 可用。

---

# 5. 项目目录结构

建议使用 monorepo 结构：

```text
knowflow-ai/
├── frontend/                 # Vue3 前端
├── backend/                  # FastAPI 后端
├── docker/                   # Docker 配置
├── docs/                     # 项目文档
├── scripts/                  # 初始化脚本
├── docker-compose.yml
├── .env.example
├── README.md
└── Makefile
```

---

# 6. Docker Compose 基础服务

在根目录创建 `docker-compose.yml`。

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    container_name: knowflow-postgres
    environment:
      POSTGRES_USER: knowflow
      POSTGRES_PASSWORD: knowflow_password
      POSTGRES_DB: knowflow_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    container_name: knowflow-redis
    ports:
      - "6379:6379"

  etcd:
    image: quay.io/coreos/etcd:v3.5.18
    container_name: knowflow-etcd
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd
    volumes:
      - etcd_data:/etcd

  minio:
    image: minio/minio:RELEASE.2025-04-22T22-12-26Z
    container_name: knowflow-minio
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: minio server /minio_data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/minio_data

  milvus:
    image: milvusdb/milvus:v2.5.10
    container_name: knowflow-milvus
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - etcd
      - minio
    volumes:
      - milvus_data:/var/lib/milvus

volumes:
  postgres_data:
  etcd_data:
  minio_data:
  milvus_data:
```

启动基础服务：
打开 Docker软件然后

```bash
docker compose up -d
```

查看运行状态：

```bash
docker compose ps
```

停止服务：

```bash
docker compose down
```

如果要清空所有数据：

```bash
docker compose down -v
```

---

# 7. 环境变量设计

在根目录创建 `.env.example`。

```env
# App
APP_NAME=KnowFlow AI
APP_ENV=development
APP_DEBUG=true

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173

# PostgreSQL
DATABASE_URL=postgresql+psycopg2://knowflow:knowflow_password@localhost:5432/knowflow_db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=document_chunks

# LLM
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=your_api_key_here
LLM_MODEL=deepseek-chat

# Embedding
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://api.your-embedding-provider.com
EMBEDDING_API_KEY=your_embedding_key_here
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIMENSION=1024

# RAG
RAG_TOP_K=5
RAG_SCORE_THRESHOLD=0.3
RAG_MAX_CONTEXT_CHARS=8000
```

复制为实际配置：

```bash
cp .env.example .env
```

---

# 8. 后端从 0 到 1 搭建

## 8.1 创建后端目录

```bash
mkdir backend
cd backend
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 8.2 安装依赖

创建 `backend/requirements.txt`：

```txt
fastapi==0.115.12
uvicorn[standard]==0.34.2
pydantic==2.11.4
pydantic-settings==2.9.1
python-dotenv==1.1.0
sqlalchemy==2.0.40
psycopg2-binary==2.9.10
alembic==1.15.2
redis==5.2.1
celery==5.5.2
python-multipart==0.0.20
pypdf==5.4.0
python-docx==1.1.2
langchain==0.3.25
langchain-community==0.3.24
langchain-openai==0.3.16
langchain-milvus==0.1.10
pymilvus==2.5.10
tiktoken==0.9.0
httpx==0.28.1
orjson==3.10.18
loguru==0.7.3
openai==1.78.1
```

安装：-
进入backend文件夹 先执行：.venv\Scripts\Activate.ps1  激活 Python 虚拟环境（否则包会装到系统全局环境）
然后
```bash
pip install -r requirements.txt
```

## 8.3 后端目录结构

```text
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── knowledge_bases.py
│   │   │   ├── documents.py
│   │   │   ├── chat.py
│   │   │   ├── prompts.py
│   │   │   ├── models.py
│   │   │   └── evaluations.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── models/
│   │   ├── user.py
│   │   ├── knowledge_base.py
│   │   ├── document.py
│   │   ├── chunk.py
│   │   ├── chat.py
│   │   ├── prompt.py
│   │   └── evaluation.py
│   ├── schemas/
│   │   ├── document.py
│   │   ├── chat.py
│   │   └── common.py
│   ├── services/
│   │   ├── document_parser.py
│   │   ├── text_splitter.py
│   │   ├── embedding_service.py
│   │   ├── vector_store.py
│   │   ├── retrieval_service.py
│   │   ├── llm_service.py
│   │   ├── prompt_service.py
│   │   ├── token_service.py
│   │   └── evaluation_service.py
│   ├── tasks/
│   │   ├── celery_app.py
│   │   └── document_tasks.py
│   ├── main.py
│   └── __init__.py
├── uploads/
├── alembic/
├── alembic.ini
├── requirements.txt
└── .env
```

## 8.4 配置文件

`backend/app/core/config.py`

```python
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    app_name: str = "KnowFlow AI"
    app_env: str = "development"
    app_debug: bool = True

    database_url: str
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str

    cors_origins: str = "http://localhost:5173"

    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "document_chunks"

    llm_provider: str = "openai_compatible"
    llm_base_url: str
    llm_api_key: str
    llm_model: str = "deepseek-chat"

    embedding_provider: str = "openai_compatible"
    embedding_base_url: str
    embedding_api_key: str
    embedding_model: str
    embedding_dimension: int = 1024

    rag_top_k: int = 5
    rag_score_threshold: float = 0.3
    rag_max_context_chars: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def cors_origin_list(self) -> List[str]:
        return [item.strip() for item in self.cors_origins.split(",")]


settings = Settings()
```

## 8.5 数据库连接

`backend/app/core/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## 8.6 FastAPI 入口

`backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import documents, chat, knowledge_bases, prompts, models, evaluations

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(knowledge_bases.router, prefix="/api/v1/knowledge-bases", tags=["Knowledge Bases"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["Prompts"])
app.include_router(models.router, prefix="/api/v1/models", tags=["Models"])
app.include_router(evaluations.router, prefix="/api/v1/evaluations", tags=["Evaluations"])


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}
```

启动后端：

```bash
uvicorn app.main:app --reload --port 8000
```

访问：

```text
http://localhost:8000/docs
```

---

# 9. 数据库表设计

## 9.1 核心表

### users

```text
id
username
email
hashed_password
created_at
updated_at
```

### knowledge_bases

```text
id
name
description
owner_id
created_at
updated_at
```

### documents

```text
id
knowledge_base_id
file_name
file_type
file_path
file_size
status
error_message
chunk_count
created_at
updated_at
```

status 可选值：

```text
uploaded
parsing
chunking
embedding
indexed
failed
```

### document_chunks

```text
id
document_id
knowledge_base_id
chunk_index
content
content_hash
page_number
token_count
vector_id
metadata
created_at
```

### chat_sessions

```text
id
knowledge_base_id
user_id
title
created_at
updated_at
```

### chat_messages

```text
id
session_id
role
content
token_count
created_at
```

role 可选值：

```text
user
assistant
system
```

### chat_references

```text
id
message_id
document_id
chunk_id
score
content_preview
page_number
created_at
```

### prompt_templates

```text
id
name
description
template
is_default
created_at
updated_at
```

### model_configs

```text
id
provider
base_url
model_name
model_type
is_active
created_at
updated_at
```

model_type 可选值：

```text
chat
embedding
rerank
```

### question_feedbacks

```text
id
message_id
rating
comment
created_at
```

rating 可选值：

```text
like
dislike
```

### evaluation_cases

```text
id
knowledge_base_id
question
expected_answer
created_at
```

### evaluation_runs

```text
id
knowledge_base_id
case_count
avg_score
created_at
```

---

# 10. 后端核心模块实现思路

## 10.1 文档解析服务

`backend/app/services/document_parser.py`

职责：

- 读取 PDF
- 读取 Word
- 读取 Markdown
- 读取 TXT
- 返回纯文本和页码信息

伪代码：

```python
from pathlib import Path
from pypdf import PdfReader
from docx import Document


def parse_document(file_path: str) -> list[dict]:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(file_path)

    if suffix in [".docx", ".doc"]:
        return parse_docx(file_path)

    if suffix in [".md", ".txt"]:
        return parse_text(file_path)

    raise ValueError(f"Unsupported file type: {suffix}")


def parse_pdf(file_path: str) -> list[dict]:
    reader = PdfReader(file_path)
    pages = []

    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({
            "page_number": index + 1,
            "content": text,
        })

    return pages


def parse_docx(file_path: str) -> list[dict]:
    doc = Document(file_path)
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return [{"page_number": None, "content": text}]


def parse_text(file_path: str) -> list[dict]:
    text = Path(file_path).read_text(encoding="utf-8")
    return [{"page_number": None, "content": text}]
```

## 10.2 文本切片服务

`backend/app/services/text_splitter.py`

切片原则：

- 优先按标题、段落切
- 每个 chunk 不要太短
- 每个 chunk 不要太长
- chunk 之间保留 overlap
- 保存页码和来源信息

基础版本：

```python
def split_text(
    pages: list[dict],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[dict]:
    chunks = []

    for page in pages:
        content = page["content"]
        page_number = page.get("page_number")

        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk_text = content[start:end].strip()

            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "page_number": page_number,
                })

            start = end - chunk_overlap

    return chunks
```

后续优化：

```text
1. 按 Markdown 标题切分
2. 按自然段落切分
3. 按 Token 数切分
4. 添加 chunk overlap
5. 保留章节标题作为 metadata
```

## 10.3 Embedding 服务

`backend/app/services/embedding_service.py`

职责：

- 接收文本列表
- 调用 Embedding API
- 返回向量列表

伪代码：

```python
from openai import OpenAI
from app.core.config import settings


class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
```

## 10.4 向量库服务

`backend/app/services/vector_store.py`

职责：

- 初始化 Milvus Collection
- 写入向量
- 根据问题向量检索 TopK

建议抽象一层接口，方便后续支持 pgvector。

```python
class VectorStore:
    def add_chunks(self, chunks: list[dict]) -> None:
        raise NotImplementedError

    def search(self, query_vector: list[float], top_k: int) -> list[dict]:
        raise NotImplementedError
```

Milvus 实现逻辑：

```text
Collection 字段：
- id: 主键
- chunk_id: PostgreSQL 中的 chunk id
- knowledge_base_id
- document_id
- vector
- content
```

检索返回：

```text
chunk_id
document_id
score
content
```

## 10.5 检索服务

`backend/app/services/retrieval_service.py`

职责：

- 将用户问题转 Embedding
- 调 Milvus 检索 TopK
- 过滤低分片段
- 根据 chunk_id 查 PostgreSQL
- 返回上下文片段

伪代码：

```python
class RetrievalService:
    def __init__(self, embedding_service, vector_store):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(self, question: str, knowledge_base_id: int, top_k: int = 5):
        query_vector = self.embedding_service.embed_query(question)

        results = self.vector_store.search(
            query_vector=query_vector,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k,
        )

        return results
```

## 10.6 Prompt 组装服务

`backend/app/services/prompt_service.py`

基础 Prompt：

```text
你是企业知识库智能问答助手。
你只能根据给定的资料回答问题。
如果资料中没有答案，请回答“根据当前知识库资料，无法确认该问题”。
不要编造不存在的信息。
回答后请尽量说明依据来自哪些资料。

用户问题：
{question}

知识库资料：
{context}
```

Prompt 组装：

```python
def build_rag_prompt(question: str, contexts: list[dict]) -> str:
    context_text = "\n\n".join([
        f"[来源 {index + 1}] 文档：{item['document_name']}，页码：{item.get('page_number')}\n{item['content']}"
        for index, item in enumerate(contexts)
    ])

    return f"""
你是企业知识库智能问答助手。
你只能根据给定的资料回答问题。
如果资料中没有答案，请回答“根据当前知识库资料，无法确认该问题”。
不要编造不存在的信息。
回答后请尽量说明依据来自哪些资料。

用户问题：
{question}

知识库资料：
{context_text}
"""
```

## 10.7 LLM 服务

`backend/app/services/llm_service.py`

职责：

- 统一封装不同厂商模型
- 支持 OpenAI-compatible API
- 支持流式输出
- 统计 Token

伪代码：

```python
from openai import OpenAI
from app.core.config import settings


class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

    def stream_chat(self, prompt: str):
        stream = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=True,
            temperature=0.2,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
```

## 10.8 Chat 流式接口

`backend/app/api/v1/chat.py`

```python
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class ChatStreamRequest(BaseModel):
    knowledge_base_id: int
    question: str
    session_id: int | None = None
    top_k: int = 5


@router.post("/stream")
def chat_stream(payload: ChatStreamRequest):
    def event_generator():
        references = []
        yield f"event: references\ndata: {json.dumps(references, ensure_ascii=False)}\n\n"

        yield f"event: token\ndata: {json.dumps({'content': '这是流式回答示例。'}, ensure_ascii=False)}\n\n"

        yield f"event: done\ndata: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
```

---

# 11. Celery 异步任务设计

## 11.1 Celery 配置

`backend/app/tasks/celery_app.py`

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "knowflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.task_routes = {
    "app.tasks.document_tasks.process_document": "documents",
}
```

## 11.2 文档处理任务

`backend/app/tasks/document_tasks.py`

```python
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.document_tasks.process_document")
def process_document(document_id: int):
    """
    1. 查询 document
    2. 更新状态 parsing
    3. 解析文档
    4. 更新状态 chunking
    5. 文本切片
    6. 更新状态 embedding
    7. 生成 embedding
    8. 写 PostgreSQL chunks
    9. 写 Milvus vectors
    10. 更新状态 indexed
    """
    return {"document_id": document_id, "status": "indexed"}
```

启动 Worker：

```bash
celery -A app.tasks.celery_app.celery_app worker -Q documents --loglevel=info
```

---

# 12. API 设计

## 12.1 知识库 API

### 创建知识库

```http
POST /api/v1/knowledge-bases
```

请求：

```json
{
  "name": "公司制度知识库",
  "description": "存放公司制度、流程、政策文档"
}
```

响应：

```json
{
  "id": 1,
  "name": "公司制度知识库",
  "description": "存放公司制度、流程、政策文档"
}
```

### 查询知识库列表

```http
GET /api/v1/knowledge-bases
```

---

## 12.2 文档 API

### 上传文档

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
```

表单字段：

```text
knowledge_base_id
file
```

响应：

```json
{
  "document_id": 12,
  "file_name": "员工手册.pdf",
  "status": "uploaded",
  "task_id": "celery-task-id"
}
```

### 查询文档状态

```http
GET /api/v1/documents/{document_id}
```

响应：

```json
{
  "id": 12,
  "file_name": "员工手册.pdf",
  "status": "indexed",
  "chunk_count": 26
}
```

### 查询知识库文档列表

```http
GET /api/v1/knowledge-bases/{knowledge_base_id}/documents
```

---

## 12.3 聊天 API

### 流式问答

```http
POST /api/v1/chat/stream
```

请求：

```json
{
  "knowledge_base_id": 1,
  "question": "员工年假规则是什么？",
  "session_id": null,
  "top_k": 5
}
```

SSE 事件：

```text
event: references
data: [{"document_name":"员工手册.pdf","page_number":3,"content":"..."}]

event: token
data: {"content":"根据员工手册..."}

event: token
data: {"content":"员工年假..."}

event: done
data: {"done":true}
```

### 获取会话历史

```http
GET /api/v1/chat/sessions/{session_id}/messages
```

---

## 12.4 反馈 API

### 点赞 / 点踩

```http
POST /api/v1/evaluations/feedback
```

请求：

```json
{
  "message_id": 100,
  "rating": "like",
  "comment": "回答准确"
}
```

---

# 13. 前端从 0 到 1 搭建

## 13.1 创建 Vue3 项目

在根目录执行：

```bash
pnpm create vite frontend --template vue-ts
cd frontend
pnpm install
```

启动：

```bash
pnpm dev
```

访问：

```text
http://localhost:5173
```

## 13.2 安装前端依赖

```bash
pnpm add ant-design-vue @ant-design/icons-vue pinia vue-router axios
pnpm add markdown-it highlight.js
pnpm add @vueuse/core
pnpm add echarts vue-echarts
```

开发依赖：

```bash
pnpm add -D unplugin-vue-components unplugin-auto-import
```

## 13.3 前端目录结构

```text
frontend/
├── src/
│   ├── api/
│   │   ├── http.ts
│   │   ├── knowledgeBase.ts
│   │   ├── document.ts
│   │   ├── chat.ts
│   │   └── evaluation.ts
│   ├── assets/
│   ├── components/
│   │   ├── AppLayout.vue
│   │   ├── FileUploader.vue
│   │   ├── ChatMessage.vue
│   │   ├── ReferenceList.vue
│   │   ├── MarkdownRenderer.vue
│   │   └── StatusTag.vue
│   ├── pages/
│   │   ├── LoginPage.vue
│   │   ├── DashboardPage.vue
│   │   ├── KnowledgeBaseListPage.vue
│   │   ├── KnowledgeBaseDetailPage.vue
│   │   ├── ChatPage.vue
│   │   ├── PromptSettingsPage.vue
│   │   ├── ModelSettingsPage.vue
│   │   └── EvaluationPage.vue
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   ├── user.ts
│   │   ├── knowledgeBase.ts
│   │   └── chat.ts
│   ├── types/
│   │   ├── document.ts
│   │   ├── chat.ts
│   │   └── common.ts
│   ├── utils/
│   │   ├── sse.ts
│   │   └── format.ts
│   ├── App.vue
│   └── main.ts
├── .env.development
├── package.json
└── vite.config.ts
```

## 13.4 配置 Ant Design Vue 和 Pinia

`frontend/src/main.ts`

```ts
import { createApp } from 'vue'
import Antd from 'ant-design-vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

import 'ant-design-vue/dist/reset.css'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Antd)

app.mount('#app')
```

## 13.5 配置路由

`frontend/src/router/index.ts`

```ts
import { createRouter, createWebHistory } from 'vue-router'
import DashboardPage from '@/pages/DashboardPage.vue'
import KnowledgeBaseListPage from '@/pages/KnowledgeBaseListPage.vue'
import KnowledgeBaseDetailPage from '@/pages/KnowledgeBaseDetailPage.vue'
import ChatPage from '@/pages/ChatPage.vue'
import PromptSettingsPage from '@/pages/PromptSettingsPage.vue'
import ModelSettingsPage from '@/pages/ModelSettingsPage.vue'
import EvaluationPage from '@/pages/EvaluationPage.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: DashboardPage },
  { path: '/knowledge-bases', component: KnowledgeBaseListPage },
  { path: '/knowledge-bases/:id', component: KnowledgeBaseDetailPage },
  { path: '/chat/:knowledgeBaseId', component: ChatPage },
  { path: '/settings/prompts', component: PromptSettingsPage },
  { path: '/settings/models', component: ModelSettingsPage },
  { path: '/evaluations', component: EvaluationPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

注意：如果使用 `@` 路径别名，需要在 `vite.config.ts` 中配置。

## 13.6 配置 Vite 路径别名

`frontend/vite.config.ts`

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

## 13.7 API 请求封装

`frontend/src/api/http.ts`

```ts
import axios from 'axios'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  },
)
```

## 13.8 类型定义

`frontend/src/types/document.ts`

```ts
export type DocumentStatus =
  | 'uploaded'
  | 'parsing'
  | 'chunking'
  | 'embedding'
  | 'indexed'
  | 'failed'

export interface KnowledgeDocument {
  id: number
  knowledge_base_id: number
  file_name: string
  file_type: string
  file_size: number
  status: DocumentStatus
  error_message?: string
  chunk_count: number
  created_at: string
}
```

`frontend/src/types/chat.ts`

```ts
export interface ChatReference {
  document_id: number
  document_name: string
  chunk_id: number
  page_number?: number
  score: number
  content: string
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant' | 'system'
  content: string
  references?: ChatReference[]
  loading?: boolean
}
```

## 13.9 文档上传组件

`frontend/src/components/FileUploader.vue`

```vue
<template>
  <a-upload-dragger
    name="file"
    :multiple="false"
    :custom-request="handleUpload"
    :show-upload-list="false"
    accept=".pdf,.doc,.docx,.md,.txt"
  >
    <p class="ant-upload-drag-icon">📄</p>
    <p class="ant-upload-text">点击或拖拽文件上传</p>
    <p class="ant-upload-hint">支持 PDF、Word、Markdown、TXT</p>
  </a-upload-dragger>
</template>

<script setup lang="ts">
import { message } from 'ant-design-vue'
import { uploadDocument } from '@/api/document'

const props = defineProps<{
  knowledgeBaseId: number
}>()

const emit = defineEmits<{
  uploaded: []
}>()

async function handleUpload(options: any) {
  try {
    const formData = new FormData()
    formData.append('knowledge_base_id', String(props.knowledgeBaseId))
    formData.append('file', options.file)

    await uploadDocument(formData)

    message.success('上传成功，文档正在解析')
    emit('uploaded')
  } catch (error) {
    message.error('上传失败')
    options.onError(error)
  }
}
</script>
```

`frontend/src/api/document.ts`

```ts
import { http } from './http'

export function uploadDocument(formData: FormData) {
  return http.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function getDocumentsByKnowledgeBase(knowledgeBaseId: number) {
  return http.get(`/knowledge-bases/${knowledgeBaseId}/documents`)
}

export function getDocument(documentId: number) {
  return http.get(`/documents/${documentId}`)
}
```

## 13.10 聊天页面核心逻辑

`frontend/src/pages/ChatPage.vue`

```vue
<template>
  <div class="chat-page">
    <div class="messages">
      <ChatMessage
        v-for="(message, index) in messages"
        :key="index"
        :message="message"
      />
    </div>

    <div class="chat-input">
      <a-textarea
        v-model:value="question"
        placeholder="请输入你的问题"
        :auto-size="{ minRows: 2, maxRows: 6 }"
        @pressEnter.prevent="handleSend"
      />
      <a-button type="primary" :loading="loading" @click="handleSend">
        发送
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import ChatMessage from '@/components/ChatMessage.vue'
import type { ChatMessage as ChatMessageType } from '@/types/chat'
import { streamChat } from '@/api/chat'

const route = useRoute()
const knowledgeBaseId = Number(route.params.knowledgeBaseId)

const question = ref('')
const loading = ref(false)
const messages = ref<ChatMessageType[]>([])

async function handleSend() {
  if (!question.value.trim() || loading.value) return

  const userQuestion = question.value.trim()
  question.value = ''

  messages.value.push({
    role: 'user',
    content: userQuestion,
  })

  const assistantMessage: ChatMessageType = {
    role: 'assistant',
    content: '',
    references: [],
    loading: true,
  }

  messages.value.push(assistantMessage)
  loading.value = true

  try {
    await streamChat({
      knowledge_base_id: knowledgeBaseId,
      question: userQuestion,
      top_k: 5,
      onReferences: (references) => {
        assistantMessage.references = references
      },
      onToken: (token) => {
        assistantMessage.content += token
      },
      onDone: () => {
        assistantMessage.loading = false
      },
    })
  } finally {
    loading.value = false
    assistantMessage.loading = false
  }
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.chat-input {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid #eee;
}
</style>
```

## 13.11 SSE 请求封装

浏览器原生 `EventSource` 只支持 GET，不方便发送 POST JSON。
本项目推荐用 `fetch + ReadableStream` 处理 POST 流式响应。

`frontend/src/api/chat.ts`

```ts
import type { ChatReference } from '@/types/chat'

interface StreamChatOptions {
  knowledge_base_id: number
  question: string
  session_id?: number
  top_k?: number
  onReferences?: (references: ChatReference[]) => void
  onToken?: (token: string) => void
  onDone?: () => void
  onError?: (error: unknown) => void
}

export async function streamChat(options: StreamChatOptions) {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: localStorage.getItem('token')
        ? `Bearer ${localStorage.getItem('token')}`
        : '',
    },
    body: JSON.stringify({
      knowledge_base_id: options.knowledge_base_id,
      question: options.question,
      session_id: options.session_id,
      top_k: options.top_k || 5,
    }),
  })

  if (!response.body) {
    throw new Error('当前浏览器不支持流式响应')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()

    if (done) break

    buffer += decoder.decode(value, { stream: true })

    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const eventText of events) {
      const lines = eventText.split('\n')
      const eventLine = lines.find((line) => line.startsWith('event:'))
      const dataLine = lines.find((line) => line.startsWith('data:'))

      if (!eventLine || !dataLine) continue

      const eventName = eventLine.replace('event:', '').trim()
      const data = JSON.parse(dataLine.replace('data:', '').trim())

      if (eventName === 'references') {
        options.onReferences?.(data)
      }

      if (eventName === 'token') {
        options.onToken?.(data.content)
      }

      if (eventName === 'done') {
        options.onDone?.()
      }

      if (eventName === 'error') {
        options.onError?.(data)
      }
    }
  }
}
```

## 13.12 ChatMessage 组件

`frontend/src/components/ChatMessage.vue`

```vue
<template>
  <div :class="['chat-message', message.role]">
    <div class="role">
      {{ message.role === 'user' ? '我' : 'AI 助手' }}
    </div>

    <div class="content">
      <MarkdownRenderer :content="message.content" />
      <a-spin v-if="message.loading" size="small" />
    </div>

    <ReferenceList
      v-if="message.references?.length"
      :references="message.references"
    />
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from '@/types/chat'
import MarkdownRenderer from './MarkdownRenderer.vue'
import ReferenceList from './ReferenceList.vue'

defineProps<{
  message: ChatMessage
}>()
</script>

<style scoped>
.chat-message {
  margin-bottom: 20px;
}

.role {
  font-weight: 600;
  margin-bottom: 8px;
}

.content {
  background: #f7f8fa;
  padding: 12px 16px;
  border-radius: 8px;
}

.chat-message.user .content {
  background: #e6f4ff;
}
</style>
```

---

# 14. 核心页面规划

## 14.1 DashboardPage

展示：

- 知识库数量
- 文档数量
- 问答次数
- Token 消耗
- 最近上传文档
- 最近问答记录

## 14.2 KnowledgeBaseListPage

功能：

- 新建知识库
- 查看知识库列表
- 编辑知识库
- 删除知识库
- 进入知识库详情
- 进入知识库问答

## 14.3 KnowledgeBaseDetailPage

功能：

- 展示知识库信息
- 上传文档
- 文档列表
- 文档处理状态
- 文档删除
- 重新解析
- 查看切片数量

## 14.4 ChatPage

功能：

- 基于指定知识库提问
- 流式展示回答
- 展示引用来源
- 展开引用片段
- 查看历史会话
- 点赞 / 点踩反馈

## 14.5 PromptSettingsPage

功能：

- 查看默认 Prompt
- 编辑系统 Prompt
- 新建 Prompt 模板
- 设置默认模板

## 14.6 ModelSettingsPage

功能：

- 配置模型供应商
- 配置 Base URL
- 配置模型名称
- 配置 Temperature
- 测试模型连通性

## 14.7 EvaluationPage

功能：

- 查看问答日志
- 查看检索 TopK
- 查看引用命中情况
- 查看 Token 消耗
- 查看响应时间
- 查看点赞 / 点踩反馈

---

# 15. 开发顺序建议

## 第 1 阶段：项目骨架

目标：前后端都能跑起来。

完成事项：

```text
1. 创建 monorepo
2. 创建 docker-compose.yml
3. 启动 PostgreSQL、Redis、Milvus
4. 创建 FastAPI 项目
5. 创建 Vue3 项目
6. 配置前后端代理
7. 打通 /health 接口
```

验收标准：

```text
前端能访问 http://localhost:5173
后端能访问 http://localhost:8000/docs
前端能请求后端 /health
Docker 服务全部正常运行
```

---

## 第 2 阶段：知识库和文档管理

目标：完成文档上传基础链路。

完成事项：

```text
1. 设计 knowledge_bases 表
2. 设计 documents 表
3. 实现知识库 CRUD
4. 实现文件上传接口
5. 前端实现知识库列表页
6. 前端实现知识库详情页
7. 前端实现文档上传组件
8. 前端展示文档状态
```

验收标准：

```text
用户可以创建知识库
用户可以上传文档
PostgreSQL 中有文档记录
前端可以看到文档状态
```

---

## 第 3 阶段：文档解析与切片

目标：上传文件后自动解析并切片。

完成事项：

```text
1. 实现 PDF 解析
2. 实现 Word 解析
3. 实现 TXT / Markdown 解析
4. 实现基础文本切片
5. 设计 document_chunks 表
6. Celery 处理解析任务
7. 更新文档状态
8. 前端轮询状态
```

验收标准：

```text
上传 PDF 后状态依次变化：
uploaded → parsing → chunking → indexed

数据库中可以看到 chunks
```

---

## 第 4 阶段：Embedding 和向量入库

目标：文档切片能够向量化并写入 Milvus。

完成事项：

```text
1. 封装 EmbeddingService
2. 初始化 Milvus Collection
3. 实现 chunk 向量写入
4. 记录 vector_id
5. 实现基础向量检索测试脚本
```

验收标准：

```text
上传文档后，PostgreSQL 有 chunk
Milvus 中有对应向量
输入一个问题，可以检索到相关 chunk
```

---

## 第 5 阶段：RAG 问答接口

目标：后端可以完成完整 RAG 问答。

完成事项：

```text
1. 实现 query embedding
2. 实现 Milvus TopK 检索
3. 根据 chunk_id 查询 PostgreSQL
4. 实现 Prompt 组装
5. 封装 LLMService
6. 实现 /chat/stream
7. 保存会话和消息
8. 保存引用来源
```

验收标准：

```text
调用 /chat/stream 可以得到流式回答
回答内容基于上传文档
返回引用来源
聊天记录保存到数据库
```

---

## 第 6 阶段：前端聊天体验

目标：完成可演示的 AI 问答界面。

完成事项：

```text
1. 实现 ChatPage
2. 实现流式输出
3. 实现 Markdown 渲染
4. 实现引用来源展示
5. 实现引用片段展开
6. 实现问答历史
7. 实现点赞 / 点踩
```

验收标准：

```text
用户选择知识库后可以提问
AI 回答逐字输出
回答下方展示来源文档
用户可以点开引用片段
```

---

## 第 7 阶段：配置和评测

目标：让项目更像企业级 AI 应用。

完成事项：

```text
1. 模型配置页面
2. Prompt 配置页面
3. Token 统计
4. 响应耗时统计
5. 问答日志页面
6. 用户反馈页面
7. 简单评估指标
```

验收标准：

```text
可以切换模型配置
可以查看 Prompt
可以查看 Token 消耗
可以查看每次问答的引用来源和用户反馈
```

---

# 16. RAG 关键设计细节

## 16.1 切片策略

MVP 阶段：

```text
chunk_size = 800 字符
chunk_overlap = 120 字符
```

进阶阶段：

```text
1. Markdown 按标题切
2. PDF 按页码切
3. 长段落按 Token 切
4. 短段落合并
5. 每个 chunk 保留标题路径
```

## 16.2 检索策略

MVP 阶段：

```text
用户问题 → Embedding → Milvus TopK → 拼接 Prompt
```

进阶阶段：

```text
用户问题
  ↓
Query Rewrite
  ↓
向量检索 + 关键词检索
  ↓
Rerank
  ↓
去重
  ↓
上下文压缩
  ↓
Prompt 拼接
```

## 16.3 Prompt 防幻觉策略

Prompt 中必须明确约束：

```text
1. 只能根据给定资料回答
2. 不知道就说无法确认
3. 不要编造
4. 回答要附带引用依据
5. 遇到资料冲突要说明冲突
```

## 16.4 引用来源设计

每个引用来源至少包含：

```text
document_name
page_number
chunk_content
score
```

前端展示时建议：

```text
来源 1：员工手册.pdf，第 3 页
片段：员工入职满一年后享有 5 天带薪年假……
相似度：0.82
```

## 16.5 Token 统计

MVP 可以先估算：

```text
1 个中文字符约等于 1 个 token 的粗略估算
```

后续用 tokenizer 精确统计。

需要统计：

```text
question_tokens
context_tokens
answer_tokens
total_tokens
```

---

# 17. 简单 Rerank 方案

MVP 可以先不接专门的 Rerank 模型，用规则重排：

```text
score = 向量相似度分数
如果 chunk 中包含问题关键词，加分
如果 chunk 来自标题匹配文档，加分
如果 chunk 太短，降分
如果 chunk 重复，去重
```

伪代码：

```python
def simple_rerank(question: str, chunks: list[dict]) -> list[dict]:
    keywords = [word for word in question.split() if len(word) > 1]

    for chunk in chunks:
        bonus = 0
        content = chunk["content"]

        for keyword in keywords:
            if keyword in content:
                bonus += 0.05

        if len(content) < 100:
            bonus -= 0.03

        chunk["final_score"] = chunk["score"] + bonus

    return sorted(chunks, key=lambda x: x["final_score"], reverse=True)
```

后续可以接入：

```text
bge-reranker
Cohere Rerank
通义 Rerank
智谱 Rerank
```

---

# 18. 问答效果评估设计

## 18.1 基础指标

MVP 阶段做这些即可：

```text
1. 是否召回到引用
2. TopK 召回数量
3. 用户是否点赞
4. 回答是否为空
5. 是否触发“无法确认”
6. 响应时间
7. Token 消耗
```

## 18.2 评估页面展示

建议图表：

```text
1. 每日问答次数
2. 平均响应时间
3. 平均 Token 消耗
4. 点赞 / 点踩比例
5. 无召回问题列表
6. 低分召回问题列表
```

## 18.3 批量评测

准备一批测试问题：

```json
[
  {
    "question": "员工年假如何计算？",
    "expected_answer": "根据入职年限计算……"
  },
  {
    "question": "报销需要多久内提交？",
    "expected_answer": "发票开具后 30 天内……"
  }
]
```

系统自动跑问答并记录：

```text
question
answer
references
latency_ms
token_count
human_score
```

---

# 19. 部署建议

## 19.1 本地开发部署

```text
前端：pnpm dev
后端：uvicorn app.main:app --reload
Celery：celery worker
基础服务：docker compose up -d
```

## 19.2 一键启动脚本

可以写 Makefile：

```makefile
up:
	docker compose up -d

down:
	docker compose down

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

worker:
	cd backend && celery -A app.tasks.celery_app.celery_app worker -Q documents --loglevel=info

frontend:
	cd frontend && pnpm dev
```

运行：

```bash
make up
make backend
make worker
make frontend
```

## 19.3 生产部署建议

生产环境可以使用：

```text
Nginx
Docker Compose
PostgreSQL
Redis
Milvus
FastAPI + Gunicorn/Uvicorn
Celery Worker
前端静态文件
```

---

# 20. GitHub README 应该包含什么

你的 README 不要只写启动命令，应该包括：

```text
1. 项目简介
2. 项目截图
3. 在线演示地址
4. 技术栈
5. 系统架构图
6. RAG 流程图
7. 功能列表
8. 本地启动步骤
9. 环境变量说明
10. 数据库设计
11. API 文档
12. 项目难点
13. 后续规划
```

## 20.1 README 项目亮点写法

```text
项目亮点：

1. 实现企业知识库 RAG 问答完整链路：文档上传、解析、切片、Embedding、向量检索、Prompt 组装、大模型流式回答。
2. 基于 FastAPI + Celery 实现文档异步解析和向量化，避免接口阻塞。
3. 基于 Milvus 实现语义检索，并支持 TopK、相似度阈值和简单 Rerank。
4. 前端基于 Vue3 + TypeScript + Ant Design Vue 实现类 ChatGPT 的流式问答体验。
5. 支持引用来源展示、命中文档片段展开、问答历史、用户反馈和 Token 统计。
6. 预留模型供应商抽象，支持 OpenAI-compatible API 与国内主流模型 API。
```

---

# 21. 简历项目描述

可以这样写：

```text
KnowFlow AI 企业知识库 RAG 智能问答系统

项目描述：
独立设计并实现企业知识库 RAG 智能问答系统，支持 PDF / Word / Markdown / TXT 文档上传、异步解析、文本切片、Embedding 向量化、Milvus 语义检索、大模型流式问答、引用来源展示、问答历史和用户反馈标注。

技术栈：
Vue3、TypeScript、Ant Design Vue、Pinia、FastAPI、SQLAlchemy、PostgreSQL、Redis、Celery、Milvus、LangChain、Docker Compose。

核心职责：
1. 负责前端整体架构设计，完成知识库管理、文档上传、聊天问答、引用来源展示和评测面板。
2. 负责 FastAPI 后端接口设计，实现文档管理、RAG 问答、模型配置、Prompt 模板和用户反馈接口。
3. 使用 Celery + Redis 处理文档解析、文本切片、Embedding 生成和向量入库等耗时任务。
4. 使用 Milvus 存储文档切片向量，实现基于用户问题的 TopK 语义检索。
5. 设计 Prompt 模板，约束大模型基于知识库资料回答，降低幻觉风险。
6. 使用 SSE 实现大模型回答流式输出，提升用户问答体验。
7. 实现 Token 统计、响应耗时统计、点赞 / 点踩反馈和基础问答效果评估。
```

---

# 22. 面试讲解顺序

面试时可以按这个顺序讲：

```text
1. 为什么做这个项目
2. 系统整体架构
3. 文档上传后发生了什么
4. RAG 问答流程
5. 为什么使用 PostgreSQL + Milvus
6. 为什么使用 Redis + Celery
7. 如何实现流式输出
8. 如何展示引用来源
9. 如何降低幻觉
10. 如何做效果评估
11. 项目遇到的问题和优化
12. 后续如何升级到 Agent UI
```

## 22.1 典型回答：为什么用 PostgreSQL + Milvus？

```text
PostgreSQL 用来存储结构化业务数据，例如用户、知识库、文档、切片元数据、聊天记录、引用来源和用户反馈。

Milvus 用来存储文本切片的向量并进行语义相似度检索。

两者不是重复关系，而是分工关系：PostgreSQL 负责业务数据和事务，Milvus 负责向量检索和 TopK 召回。
```

## 22.2 典型回答：为什么用 Celery？

```text
文档解析、文本切片和 Embedding 生成都是耗时任务，如果放在 HTTP 请求中同步执行，会导致接口超时和用户等待过久。

所以我使用 Redis + Celery 做异步任务。用户上传文件后，后端立即创建文档记录并返回，后台 Worker 继续处理文档，前端通过轮询或状态接口查看处理进度。
```

## 22.3 典型回答：如何降低 RAG 幻觉？

```text
我主要从四个方面处理：

1. Prompt 中要求模型只能根据给定资料回答，不知道就说无法确认。
2. 回答结果展示引用来源，让用户可以追溯答案依据。
3. 对检索结果设置相似度阈值，如果没有高质量片段，就不强行回答。
4. 通过用户反馈和问答日志收集低质量案例，后续优化切片、检索和 Prompt。
```

---

# 23. MVP 验收清单

## 23.1 后端验收

```text
[ ] FastAPI 服务可启动
[ ] PostgreSQL 可连接
[ ] Redis 可连接
[ ] Milvus 可连接
[ ] 知识库 CRUD 可用
[ ] 文档上传可用
[ ] 文档状态可更新
[ ] PDF 可解析
[ ] 文本可切片
[ ] Embedding 可生成
[ ] 向量可写入 Milvus
[ ] 问题可检索 TopK 片段
[ ] Prompt 可正确拼接
[ ] LLM 可调用
[ ] SSE 可流式返回
[ ] 聊天记录可保存
[ ] 引用来源可保存
```

## 23.2 前端验收

```text
[ ] 前端项目可启动
[ ] 路由可访问
[ ] Ant Design Vue 样式正常
[ ] 知识库列表可展示
[ ] 可创建知识库
[ ] 可上传文档
[ ] 文档状态可展示
[ ] 可进入聊天页面
[ ] 可发送问题
[ ] 可看到流式回答
[ ] 可看到引用来源
[ ] 可展开引用片段
[ ] 可查看问答历史
[ ] 可点赞 / 点踩
```

## 23.3 简历验收

```text
[ ] GitHub 仓库完整
[ ] README 详细
[ ] 有项目截图
[ ] 有架构图
[ ] 有本地启动说明
[ ] 有接口文档
[ ] 有演示视频
[ ] 有一段清晰的简历项目描述
```

---

# 24. 后续升级方向

## 24.1 短期升级

```text
1. 支持更多文件类型
2. 支持多知识库检索
3. 支持模型切换
4. 支持 Prompt 模板管理
5. 支持用户权限
6. 支持文档重解析
7. 支持引用片段高亮
```

## 24.2 中期升级

```text
1. Hybrid Search：关键词检索 + 向量检索
2. Rerank 模型
3. Query Rewrite
4. 多轮对话上下文压缩
5. RAG 批量评测
6. 管理后台
7. Token 成本面板
```

## 24.3 两年后转 Agent UI 的升级路线

在 KnowFlow AI 基础上升级为：

```text
AgentDesk AI：企业智能体任务工作台
```

新增能力：

```text
1. Agent 任务规划展示
2. 工具调用状态展示
3. 执行步骤时间线
4. 人工确认节点
5. 工具调用日志
6. 失败重试
7. 多 Agent 协作
8. 工作流可视化
```

从普通 RAG：

```text
用户提问 → 检索知识库 → 大模型回答
```

升级为 Agent：

```text
用户目标
  ↓
Agent 判断任务类型
  ↓
选择工具
  ↓
检索知识库 / 查询数据库 / 生成报告 / 调用接口
  ↓
展示执行步骤
  ↓
必要时请求用户确认
  ↓
输出最终结果
```

这就是你未来从 AI 应用全栈转 Agent UI / Agentic UI 的自然路径。

---

# 25. 推荐开发时间线

## 第 1 周

```text
搭建前后端项目
配置 Docker Compose
跑通 PostgreSQL、Redis、Milvus
完成知识库 CRUD
```

## 第 2 周

```text
完成文档上传
完成文档解析
完成文本切片
完成 Celery 异步任务
```

## 第 3 周

```text
完成 Embedding
完成 Milvus 入库
完成 TopK 检索
完成 Prompt 组装
```

## 第 4 周

```text
完成 LLM 调用
完成 SSE 流式输出
完成聊天页面
完成引用来源展示
```

## 第 5 周

```text
完成问答历史
完成用户反馈
完成 Token 统计
完成基础评测面板
```

## 第 6 周

```text
完善 README
补充架构图
部署在线演示
录制演示视频
整理简历项目描述
```

---

# 26. 常见坑位

## 26.1 文档解析乱码

解决：

```text
1. 确认文件编码
2. TXT 使用 utf-8 读取
3. PDF 尽量先支持文字型 PDF
4. 扫描版 PDF 需要 OCR，MVP 可以先不做
```

## 26.2 切片太碎

问题：

```text
回答上下文不完整
```

解决：

```text
增加 chunk_size
增加 overlap
按标题和段落切分
```

## 26.3 检索不准

解决：

```text
1. 优化切片
2. 增加 TopK
3. 增加 Rerank
4. 使用更好的 Embedding 模型
5. 增加关键词检索
```

## 26.4 大模型胡编

解决：

```text
1. Prompt 明确要求基于资料回答
2. 没有检索结果时不调用模型或让模型回答无法确认
3. 展示引用来源
4. 增加相似度阈值
```

## 26.5 流式输出前端解析失败

解决：

```text
1. 后端严格使用 event/data 格式
2. 每个事件用 \n\n 分隔
3. 前端 buffer 不要按单个 chunk 直接 JSON.parse
4. 需要处理半包问题
```

## 26.6 Celery 找不到任务

解决：

```text
1. 确认 task name 正确
2. 确认 worker 启动路径正确
3. 确认 Celery app 导入了任务模块
4. 确认 Redis Broker 地址正确
```

---

# 27. 最终交付物清单

你最终应该交付：

```text
1. GitHub 仓库
2. README
3. 在线 Demo
4. 演示视频
5. 架构图
6. 数据库 ER 图
7. API 文档
8. RAG 设计文档
9. 简历项目描述
10. 面试讲解稿
```

---

# 28. 官方参考资料

- Vue 官方文档：https://vuejs.org/
- Vite 官方文档：https://vite.dev/
- Ant Design Vue 官方文档：https://www.antdv.com/
- Pinia 官方文档：https://pinia.vuejs.org/
- FastAPI 官方文档：https://fastapi.tiangolo.com/
- SQLAlchemy 官方文档：https://docs.sqlalchemy.org/
- PostgreSQL 官方文档：https://www.postgresql.org/docs/
- Redis 官方文档：https://redis.io/docs/latest/
- Celery 官方文档：https://docs.celeryq.dev/
- Docker Compose 官方文档：https://docs.docker.com/compose/
- Milvus 官方文档：https://milvus.io/docs
- LangChain 官方文档：https://docs.langchain.com/
- LangChain Milvus 集成文档：https://docs.langchain.com/oss/python/integrations/vectorstores/milvus

---

# 29. 最后建议

这个项目的关键不是一次性做得非常复杂，而是先把完整闭环跑通：

```text
上传文档 → 解析 → 切片 → 向量化 → 检索 → Prompt → 大模型回答 → 流式展示 → 引用来源
```

只要这个闭环稳定，你就已经具备 AI 应用全栈工程师的核心项目经验。

后续再逐步补充：

```text
异步任务
Rerank
模型配置
Prompt 管理
Token 统计
问答评估
权限系统
Agent 工具调用
```

最终你的职业路线可以从：

```text
前端开发
  ↓
AI 应用前端
  ↓
AI 应用全栈工程师
  ↓
RAG / Agent 应用工程师
  ↓
Agent UI / Agentic UI 工程师
```

这是一条非常适合前端开发者切入 AI 的路线。

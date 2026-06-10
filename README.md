# KnowFlow AI — RAG 智能问答系统

基于 RAG（检索增强生成）架构的智能知识库问答系统，支持文档上传、向量检索、多轮对话与评测。

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

---

## 环境要求

- Python 3.11+
- Docker & Docker Compose
- Git

---

## 快速开始

### 1. 克隆项目

```bash
git clone <你的仓库地址>
cd knowflow-ai
```

### 2. 配置环境变量

项目提供了 `.env.example` 模板文件，包含所有必需的环境变量及其默认值。你需要复制一份并填入自己的配置：

```bash
# 复制模板（Linux / macOS）
cp .env.example .env

# 或 Windows PowerShell
copy .env.example .env
```

然后编辑 `.env` 文件，修改以下关键配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_API_KEY` | 大模型 API 密钥 | `sk-xxxxxxxx` |
| `LLM_BASE_URL` | LLM API 地址 | `https://api.deepseek.com` |
| `EMBEDDING_API_KEY` | 嵌入模型 API 密钥 | `sk-xxxxxxxx` |
| `EMBEDDING_BASE_URL` | 嵌入服务地址 | `https://api.your-provider.com` |
| `DATABASE_URL` | PostgreSQL 连接串 | 默认即可（Docker 自动创建） |

> **为什么 `.env` 不上传？** `.env` 包含真实的 API 密钥和密码，属于敏感信息。开源项目的标准做法是：上传 `.env.example` 作为模板，开发者自行复制并填写真实值。`.env` 已在 `.gitignore` 中排除。

### 3. 启动依赖服务（Docker）

PostgreSQL、Redis、Milvus 等基础设施通过 Docker Compose 一键启动：

```bash
docker compose up -d
```

启动后验证：

```bash
docker compose ps
# 应看到 5 个容器全部为 Up 状态：postgres, redis, etcd, minio, milvus
```

### 4. 创建 Python 虚拟环境

```bash
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### 5. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

依赖清单说明：

| 包名 | 用途 |
|------|------|
| `fastapi` + `uvicorn` | Web 框架 + ASGI 服务器 |
| `sqlalchemy` + `psycopg` | ORM + PostgreSQL 驱动 |
| `alembic` | 数据库迁移 |
| `redis` + `celery` | 缓存 + 异步任务 |
| `langchain` 系列 | RAG 流程编排 |
| `pymilvus` | Milvus 向量数据库客户端 |
| `pypdf` + `python-docx` | 文档解析（PDF / Word） |
| `tiktoken` | Token 计算 |

### 6. 运行后端服务

```bash
# 在 backend 目录下，确保虚拟环境已激活
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

---

## 项目结构

```
knowflow-ai/
├── .env.example          # 环境变量模板（可上传）
├── .gitignore            # Git 忽略规则
├── docker-compose.yml    # Docker 基础服务编排
├── Makefile              # 常用命令快捷方式
├── README.md
├── backend/
│   ├── .env              # 真实环境变量（不上传，需自行创建）
│   ├── requirements.txt  # Python 依赖清单
│   ├── alembic.ini       # 数据库迁移配置
│   └── app/
│       ├── main.py       # FastAPI 应用入口
│       ├── api/v1/       # API 路由层
│       ├── core/         # 配置、数据库、安全等核心模块
│       ├── models/       # 数据库 ORM 模型
│       ├── schemas/      # Pydantic 请求/响应模型
│       ├── services/     # 业务逻辑层
│       └── tasks/        # Celery 异步任务
├── frontend/             # 前端项目
├── docs/                 # 项目文档
└── scripts/              # 辅助脚本
```

---

## 常见问题

**Q: 运行时报错 `database_url` 未配置？**
A: 检查 `.env` 文件是否存在且位于 `backend/` 目录下，确保 `DATABASE_URL` 有值。

**Q: Docker 容器启动失败？**
A: 确保端口 `5432`、`6379`、`19530`、`9000`、`9001` 未被其他程序占用。

**Q: 如何安装新的 Python 包？**
A: 安装后务必更新 `requirements.txt`：
```bash
pip install <包名>
pip freeze > requirements.txt   # 或手动添加到 requirements.txt
```

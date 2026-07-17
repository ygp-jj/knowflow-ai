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
- Node.js 20+
- Docker & Docker Compose
- Git

---

## 快速开始

当前仓库要跑通“知识库管理 + 文档管理”页面，至少需要启动：

- Docker 基础服务
- FastAPI 后端
- Vue 前端

注意：

- 后端配置实际读取的是 `backend/.env`
- 数据库表不会自动创建，第一次运行前必须手动执行建表脚本
- 当前仓库里的 Celery 异步任务链路还没有完整接好，联调管理页面时可以先不启动 worker

### 1. 克隆项目

```bash
git clone <你的仓库地址>
cd knowflow-ai
```

### 2. 配置后端环境变量

项目提供了根目录 `.env.example` 模板文件，但后端运行时默认读取的是 `backend/.env`。
先复制一份到 `backend` 目录：

```bash
# Linux / macOS
cp .env.example backend/.env

# Windows PowerShell
copy .env.example backend\.env
```

然后编辑 `backend/.env`，至少确认以下关键配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+psycopg2://knowflow:knowflow_password@localhost:5432/knowflow_db` |
| `REDIS_URL` | Redis 地址 | `redis://localhost:6379/0` |
| `MINIO_ENDPOINT` | MinIO 地址 | `localhost:9000` |
| `LLM_API_KEY` | 大模型 API 密钥 | `sk-xxxxxxxx` |
| `LLM_BASE_URL` | LLM API 地址 | `https://api.deepseek.com` |
| `EMBEDDING_API_KEY` | 嵌入模型 API 密钥 | `sk-xxxxxxxx` |
| `EMBEDDING_BASE_URL` | 嵌入服务地址 | `https://api.your-provider.com` |
| `EMBEDDING_MODEL` | 嵌入模型名 | `text-embedding-v3` |

如果你使用的是 Neon，而不是本地 Docker Postgres，只需要把 `DATABASE_URL` 改成你的 Neon 连接串。

> `backend/scripts/create_neon_tables.py` 默认就会读取 `backend/.env` 中的 `DATABASE_URL`。

### 3. 启动依赖服务（Docker）

PostgreSQL、Redis、Milvus 等基础设施通过 Docker Compose 一键启动：

```bash
docker compose up -d
```

启动后验证：

```bash
docker compose ps
# 应看到 5 个基础容器为 Up 状态：postgres, redis, etcd, minio, milvus
```

服务默认端口：

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- MinIO API: `localhost:9000`
- MinIO Console: `http://127.0.0.1:9001`
- Milvus: `localhost:19530`

### 4. 创建 Python 虚拟环境并安装后端依赖

```bash
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
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

### 5. 第一次运行先初始化数据库表

当前后端不会自动建表，所以第一次运行必须手动执行一次建表脚本：

```bash
cd backend

# 可先检查将要连接的数据库
python .\scripts\create_neon_tables.py --dry-run

# 真正执行建表
python .\scripts\create_neon_tables.py
```

如果你想写入演示数据，可再执行：

```bash
python .\scripts\seed_neon_data.py
```

### 6. 启动后端服务

```bash
# 在 backend 目录下，确保虚拟环境已激活
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

### 7. 启动前端服务

新开一个终端窗口：

```bash
cd frontend
npm install
npm run dev
```

访问：

- 前端页面：http://127.0.0.1:5173

当前前端默认请求相对路径：

- `/api/v1`

本地开发时，Vite 会把 `/api` 代理到后端。
默认代理目标是：

- `http://127.0.0.1:8000`

如果你的后端不在本机 8000 端口，可以在 `frontend/.env` 或 `frontend/.env.local` 中覆盖：

```env
VITE_PROXY_TARGET=http://你的后端地址:8000
VITE_DEFAULT_OWNER_ID=101
```

如果将来前后端分开部署，不走同域反向代理，再显式配置：

```env
VITE_API_BASE_URL=https://api.example.com
```

所以只要后端按上面的 `8000` 端口启动，前端本地联调时一般不需要再改请求地址。

### 8. 推荐联调顺序

建议按下面顺序验证整条链路：

1. 运行 `docker compose up -d`
2. 配置好 `backend/.env`
3. 在 `backend` 目录执行建表脚本
4. 启动 FastAPI 后端
5. 打开 `http://127.0.0.1:8000/docs`，先手动创建一个知识库
6. 启动 Vue 前端
7. 打开 `http://127.0.0.1:5173`，联调知识库管理页和文档管理页
8. 在文档管理页上传文件后，可去 `http://127.0.0.1:9001` 查看 MinIO 对象是否已写入

### 9. 当前版本哪些服务可以先不启动

如果你当前只验证“知识库管理 + 文档管理”页面，可以先不启动：

- Celery worker
- 文档解析异步任务

原因是当前仓库里的异步任务链路还没有完整接通，但这不影响你使用现有的知识库 CRUD 和文档上传/列表/下载/删除功能。

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
│   ├── scripts/          # 建表、seed 等辅助脚本
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
A: 检查 `backend/.env` 是否存在，并确保 `DATABASE_URL` 有值。

**Q: 后端启动了，但接口报表不存在？**
A: 说明你还没执行建表脚本。先在 `backend/` 目录运行：
```bash
python .\scripts\create_neon_tables.py
```

**Q: Docker 容器启动失败？**
A: 确保端口 `5432`、`6379`、`19530`、`9000`、`9001` 未被其他程序占用。

**Q: 前端页面打不开或接口请求失败？**
A: 先确认：
- 后端是否运行在 `http://127.0.0.1:8000`
- 前端是否运行在 `http://127.0.0.1:5173`
- `backend/.env` 里的 `CORS_ORIGINS` 是否包含 `http://localhost:5173`
- 如果你是通过局域网地址访问前端，例如 `http://10.17.223.59:5173`，还要把这个地址加入 `CORS_ORIGINS`
- 如果前端本地开发代理目标不是 `127.0.0.1:8000`，还要检查 `frontend/.env.local` 里的 `VITE_PROXY_TARGET`

**Q: 需要启动 Celery 吗？**
A: 当前版本如果只是联调知识库管理和文档管理页面，不需要。等文档异步解析链路完整接入后再启动。

**Q: 如何安装新的 Python 包？**
A: 安装后务必更新 `requirements.txt`：
```bash
pip install <包名>
pip freeze > requirements.txt   # 或手动添加到 requirements.txt
```

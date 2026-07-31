# 云服务器部署 KnowFlow AI 完整记录

> **部署时间**：2026-07-29  
> **服务器**：阿里云 ECS（华东1-杭州），2核4G，Ubuntu 24.04  
> **项目**：knowflow-ai（FastAPI + Neon PostgreSQL + MinIO + Redis）  
> **公网 IP**：动态变化（建议绑定弹性公网IP或使用域名）

---

## 一、云服务器准备

### 1.1 初始状态
- 实例规格：2核4G 经济型e
- 公网 IP：动态分配
- 操作系统：Ubuntu 24.04

### 1.2 更换操作系统（如需要）
在阿里云控制台 → 停止实例 → 更换操作系统 → 选择 **Ubuntu 24.04 64位** → 设置 root 密码。

---

## 二、开发环境配置（VS Code Remote-SSH）

### 2.1 连接服务器
- 本地 VS Code 安装 **Remote-SSH** 插件
- 配置 SSH Host：`root@<你的公网IP>`
- 首次连接需输入 root 密码

### 2.2 SSH 密钥配置（免密登录）
**本地生成密钥（如有则跳过）**：
```bash
ssh-keygen -t rsa -b 4096 -C "你的邮箱"
```

**查看并复制公钥**：
```bash
type C:\Users\你的用户名\.ssh\id_rsa.pub
```

**在服务器上添加公钥**：
```bash
mkdir -p ~/.ssh
echo "粘贴公钥内容" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 2.3 SSH 隧道配置（解决 Git 访问 GitHub 超时）
若服务器直连 GitHub 超时，可通过本地代理建立隧道：
- **本地 CMD 执行（保持窗口打开）**：
  ```bash
  ssh -R 7897:127.0.0.1:7897 root@<服务器IP>
  ```
- **服务器端配置 Git 代理**（端口替换为实际代理端口）：
  ```bash
  git config --global http.proxy http://127.0.0.1:7897
  git config --global https.proxy http://127.0.0.1:7897
  ```

---

## 三、代码迁移

### 3.1 方式选择
由于服务器直连 GitHub 不稳定，推荐 **本地压缩 + VS Code 上传**：
1. 本地将项目文件夹压缩为 `.zip`
2. VS Code 远程资源管理器中右键 → `Upload...`
3. 服务器端解压：
   ```bash
   cd /root/projects-ai
   unzip knowflow-ai.zip
   ```

### 3.2 分支切换
项目默认在 `master` 分支，需切换到 `dev`：
```bash
cd /root/projects-ai/knowflow-ai
git fetch --all
git checkout dev
git pull origin dev
```

---

## 四、Python 环境配置

### 4.1 安装系统依赖
```bash
sudo apt update
sudo apt install python3-pip python3-venv git -y
sudo apt install libpq-dev gcc -y
```

### 4.2 创建虚拟环境
```bash
cd /root/projects-ai/knowflow-ai/backend
python3 -m venv .venv
source .venv/bin/activate
```

### 4.3 安装项目依赖
`requirements.txt` 内容：
```txt
fastapi==0.115.12
uvicorn[standard]==0.34.2
pydantic==2.11.4
pydantic-settings==2.9.1
python-dotenv==1.1.0
sqlalchemy==2.0.40
psycopg2-binary==2.9.9
psycopg[binary]==3.2.3
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
minio==7.2.7
```

**安装命令**：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 五、配置文件

### 5.1 创建 `.env` 文件
```bash
cd /root/projects-ai/knowflow-ai/backend
cp .env.example .env
```

### 5.2 `.env` 关键配置
```env
DATABASE_URL=postgresql://用户名:密码@host:port/数据库名?sslmode=require
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-...
LLM_MODEL=deepseek-chat

EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-proj-...
EMBEDDING_MODEL=text-embedding-ada-002

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=knowflow-documents
MINIO_SECURE=false
```

> **注意**：`.env` 中的 `#` 注释不能跟在值后面，应单独一行。

### 5.3 修复 `config.py`（适配新版 pydantic-settings）
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ... 字段定义 ...

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
```

---

## 六、Docker 与中间件

### 6.1 安装 Docker
```bash
sudo apt update
sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
```

### 6.2 配置镜像加速器（解决拉取超时）
```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": ["https://docker.mirrors.ustc.edu.cn"]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 6.3 启动 Redis
```bash
docker run -d --name redis -p 6379:6379 redis:alpine
```

### 6.4 启动 MinIO
```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v /root/minio_data:/data \
  quay.io/minio/minio server /data --console-address ":9001"
```

### 6.5 创建 MinIO 存储桶
访问 `http://<公网IP>:9001` → 登录（minioadmin/minioadmin）→ Create Bucket → 名称 `knowflow-documents`

---

## 七、服务启动（使用 tmux）

### 7.1 启动 Docker 服务及容器
```bash
# 检查并启动 Docker 服务
sudo systemctl status docker || sudo systemctl start docker

# 启动 Redis 和 MinIO 容器
docker start redis minio

# 验证容器是否正常运行
docker ps | grep -E "redis|minio"
```

> 若容器不存在（首次部署），参考第六章的创建命令。

### 7.2 启动后端 FastAPI
```bash
tmux new -s backend
cd /root/projects-ai/knowflow-ai/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 按 Ctrl+B, D 离开会话
```

### 7.3 启动 Celery Worker
```bash
tmux new -s celery
cd /root/projects-ai/knowflow-ai/backend
source .venv/bin/activate
celery -A app.tasks.celery_app.celery_app worker -Q documents --pool=solo --loglevel=info
# 按 Ctrl+B, D 离开
```

### 7.4 启动前端 Vite
```bash
tmux new -s frontend
cd /root/projects-ai/knowflow-ai/frontend
npm run dev -- --host 0.0.0.0
# 按 Ctrl+B, D 离开
```

### 7.5 一键启动全部服务
保存为 `scripts/start-all.sh`：
赋予执行权限：chmod +x /root/start-all.sh
运行命令为：cd /root/projects-ai/knowflow-ai （项目根目录执行）然后执行：./scripts/start-all.sh
即可一键启动前后端服务

---

## 八、网络配置（安全组）

### 8.1 阿里云安全组规则
**入方向**需放行以下端口：

| 端口 | 用途 |
|------|------|
| 22 | SSH 远程连接 |
| 8000 | FastAPI 后端 |
| 9001 | MinIO 控制台 |
| 9000 | MinIO API（如需） |
| 5173 | 前端开发服务器 |

**操作路径**：ECS 控制台 → 实例 → 安全组 → 配置规则 → 添加入方向规则

### 8.2 服务器防火墙（如启用）
```bash
sudo ufw allow 22
sudo ufw allow 8000
sudo ufw allow 9000
sudo ufw allow 9001
sudo ufw allow 5173
```

---

## 九、验证与访问

| 服务 | 访问地址 | 预期结果 |
|------|----------|----------|
| FastAPI 文档 | `http://<公网IP>:8000/docs` | Swagger 页面 |
| MinIO 控制台 | `http://<公网IP>:9001` | 登录页面 |
| 前端页面 | `http://<公网IP>:5173` | 应用界面 |

---

## 十、维护脚本

### 10.1 IP 变化更新脚本
保存为 `/root/projects-ai/knowflow-ai/scripts/update_ip.sh`：
```bash
#!/bin/bash
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
NEW_IP=$(curl -s ifconfig.me)
read -p "请输入旧的 IP: " OLD_IP
FILES=(
    "$PROJECT_ROOT/frontend/vite.config.js"
    "$PROJECT_ROOT/backend/.env"
)
for file in "${FILES[@]}"; do
    [ -f "$file" ] && sed -i "s/$OLD_IP/$NEW_IP/g" "$file"
done
echo "IP 已更新为 $NEW_IP"
```
```bash
chmod +x /root/projects-ai/knowflow-ai/scripts/update_ip.sh
```
### 10.2 一键启动所有服务
保存为 scripts/start-all.sh
赋予执行权限：chmod +x scripts/start-all.sh
运行：./scripts/start-all.sh

### 10.3 一键停止所有服务
保存为 scripts/stop-all.sh
赋予执行权限：chmod +x scripts/stop-all.sh
运行：./scripts/stop-all.sh

---

## 十一、常用命令速查

| 操作 | 命令 |
|------|------|
| 查看所有 tmux 会话 | `tmux ls` |
| 进入后端日志 | `tmux attach -t backend` |
| 进入 Celery 日志 | `tmux attach -t celery` |
| 进入前端日志 | `tmux attach -t frontend` |
| 离开 tmux 会话 | `Ctrl+B, D` |
| 停止所有服务 | `tmux kill-session -t backend && tmux kill-session -t celery && tmux kill-session -t frontend` |
| 停止 Docker 容器 | `docker stop redis minio` |
| 查看端口占用 | `sudo lsof -i :8000` |

---

## 附录：常见问题速查

| 问题 | 解决方法 |
|------|----------|
| 端口占用 | `sudo lsof -i :8000` → `kill -9 PID` |
| Docker 容器未启动 | `docker start redis minio` |
| 前端代理无效 | 检查 `vite.config.js` 中的 `target` 是否正确 |
| .env 未加载 | 确认文件存在且 `config.py` 使用 `model_config` |
| Celery 连接 Redis 失败 | 确认 `docker ps | grep redis` 正常运行 |
| npm 命令未找到 | 安装 Node.js：`nvm install --lts && nvm use --lts` |

---

> **维护人**：YGP  
> **最后更新**：2026-07-31
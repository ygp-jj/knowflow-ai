#!/bin/bash
# ============================================================
# 脚本名称: start-all.sh
# 功能描述: 一键启动 KnowFlow AI 项目所需的所有服务
#          包括 Docker 容器(Redis, MinIO)、后端 API、Celery Worker、前端开发服务器
# 使用方法: cd /root/projects-ai/knowflow-ai （项目根目录执行）然后执行：./scripts/start-all.sh
# 作者: YGP
# 更新日期: 2026-07-31
# ============================================================

# 设置颜色输出，便于区分提示信息
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   KnowFlow AI 一键启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# ------------------- 1. 检查并启动 Docker 服务 -------------------
echo -e "${YELLOW}[1/5] 检查 Docker 服务...${NC}"
if systemctl is-active --quiet docker; then
    echo -e "${GREEN}  ✅ Docker 服务已运行${NC}"
else
    echo -e "${YELLOW}  ⚠️  Docker 未运行，正在启动...${NC}"
    sudo systemctl start docker
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✅ Docker 服务启动成功${NC}"
    else
        echo -e "${RED}  ❌ Docker 启动失败，请手动检查${NC}"
        exit 1
    fi
fi

# ------------------- 2. 启动 Redis 和 MinIO 容器 -------------------
echo -e "${YELLOW}[2/5] 启动 Redis 和 MinIO 容器...${NC}"

# 检查并启动 Redis
if docker ps -a --format '{{.Names}}' | grep -q "^redis$"; then
    if docker ps --format '{{.Names}}' | grep -q "^redis$"; then
        echo -e "${GREEN}  ✅ Redis 容器已在运行${NC}"
    else
        docker start redis > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✅ Redis 容器启动成功${NC}"
        else
            echo -e "${RED}  ❌ Redis 启动失败，请检查容器状态${NC}"
        fi
    fi
else
    echo -e "${YELLOW}  ⚠️  Redis 容器不存在，请先创建 (参考部署文档)${NC}"
fi

# 检查并启动 MinIO
if docker ps -a --format '{{.Names}}' | grep -q "^minio$"; then
    if docker ps --format '{{.Names}}' | grep -q "^minio$"; then
        echo -e "${GREEN}  ✅ MinIO 容器已在运行${NC}"
    else
        docker start minio > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✅ MinIO 容器启动成功${NC}"
        else
            echo -e "${RED}  ❌ MinIO 启动失败，请检查容器状态${NC}"
        fi
    fi
else
    echo -e "${YELLOW}  ⚠️  MinIO 容器不存在，请先创建 (参考部署文档)${NC}"
fi

# ------------------- 3. 启动后端 FastAPI 服务 -------------------
echo -e "${YELLOW}[3/5] 启动后端 FastAPI 服务...${NC}"
# 检查 backend 会话是否已存在，存在则先关闭
if tmux has-session -t backend 2>/dev/null; then
    echo -e "${YELLOW}  ⚠️  后端会话已存在，正在重新创建...${NC}"
    tmux kill-session -t backend
fi
tmux new -d -s backend "cd /root/projects-ai/knowflow-ai/backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ 后端服务启动成功 (tmux 会话: backend)${NC}"
else
    echo -e "${RED}  ❌ 后端启动失败，请检查日志${NC}"
fi

# ------------------- 4. 启动 Celery Worker -------------------
echo -e "${YELLOW}[4/5] 启动 Celery Worker...${NC}"
if tmux has-session -t celery 2>/dev/null; then
    echo -e "${YELLOW}  ⚠️  Celery 会话已存在，正在重新创建...${NC}"
    tmux kill-session -t celery
fi
tmux new -d -s celery "cd /root/projects-ai/knowflow-ai/backend && source .venv/bin/activate && celery -A app.tasks.celery_app.celery_app worker -Q documents --pool=solo --loglevel=info"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ Celery Worker 启动成功 (tmux 会话: celery)${NC}"
else
    echo -e "${RED}  ❌ Celery 启动失败，请检查日志${NC}"
fi

# ------------------- 5. 启动前端 Vite 开发服务器 -------------------
echo -e "${YELLOW}[5/5] 启动前端 Vite 开发服务器...${NC}"
if tmux has-session -t frontend 2>/dev/null; then
    echo -e "${YELLOW}  ⚠️  前端会话已存在，正在重新创建...${NC}"
    tmux kill-session -t frontend
fi
tmux new -d -s frontend "cd /root/projects-ai/knowflow-ai/frontend && npm run dev -- --host 0.0.0.0"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ 前端服务启动成功 (tmux 会话: frontend)${NC}"
else
    echo -e "${RED}  ❌ 前端启动失败，请检查日志${NC}"
fi

# ------------------- 输出启动结果汇总 -------------------
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 所有服务已启动完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "📋 当前 tmux 会话列表:"
tmux ls

echo -e "\n${YELLOW}🔍 查看服务日志:${NC}"
echo "  - 后端:   tmux attach -t backend"
echo "  - Celery: tmux attach -t celery"
echo "  - 前端:   tmux attach -t frontend"
echo -e "\n${YELLOW}🌐 访问地址:${NC}"
echo "  - 前端页面:      http://$(curl -s ifconfig.me):5173"
echo "  - 后端 API 文档: http://$(curl -s ifconfig.me):8000/docs"
echo "  - MinIO 控制台:  http://$(curl -s ifconfig.me):9001"
echo -e "\n${YELLOW}💡 离开 tmux 会话（不停止服务）: 按 Ctrl+B 然后按 D${NC}"
echo -e "${GREEN}========================================${NC}"
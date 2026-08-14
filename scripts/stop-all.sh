#!/bin/bash
# ============================================================
# 脚本名称: stop-all.sh
# 功能描述: 一键停止 KnowFlow AI 项目所有服务
#          关闭 tmux（后端、Celery、前端）并停止 Docker 容器
#          （Redis、MinIO、以及可选的 etcd / Milvus / Attu）
# 使用方法: cd /root/projects-ai/knowflow-ai && ./scripts/stop-all.sh
# 作者: YGP
# 更新日期: 2026-08-14
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${YELLOW}正在停止所有服务...${NC}"

# 停止 tmux 会话（如果存在）
for session in backend celery frontend; do
    if tmux has-session -t $session 2>/dev/null; then
        tmux kill-session -t $session
        echo -e "${GREEN}  ✅ 已停止 $session${NC}"
    else
        echo -e "${YELLOW}  ⚠️  $session 会话不存在，跳过${NC}"
    fi
done

# 停止 Docker 容器（如果正在运行）
for container in redis minio knowflow-milvus knowflow-etcd attu; do
    if docker ps --format '{{.Names}}' | grep -q "^$container$"; then
        docker stop $container > /dev/null 2>&1
        echo -e "${GREEN}  ✅ 已停止 $container 容器${NC}"
    else
        echo -e "${YELLOW}  ⚠️  $container 容器未运行，跳过${NC}"
    fi
done

echo -e "${GREEN}所有服务已停止${NC}"

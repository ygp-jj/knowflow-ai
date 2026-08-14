#!/bin/bash
# ============================================================
# 脚本名称: start-all.sh
# 功能描述: 一键启动 KnowFlow AI 项目所需服务
#          必启：Docker、Redis、MinIO、后端、Celery、前端
#          可选：Milvus(+etcd)、Attu（Milvus 网页查看，端口 8001）
# 使用方法:
#   cd /root/projects-ai/knowflow-ai && ./scripts/start-all.sh
#   # 非交互（跳过提问）:
#   START_MILVUS=y START_ATTU=y ./scripts/start-all.sh
#   START_MILVUS=n START_ATTU=n ./scripts/start-all.sh
# 作者: YGP
# 更新日期: 2026-08-14
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

# 国内环境优先华为云镜像（Docker Hub 常不可用）
MILVUS_IMAGE="${MILVUS_IMAGE:-swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/milvusdb/milvus:v2.4.15}"
ETCD_IMAGE="${ETCD_IMAGE:-swr.cn-north-4.myhuaweicloud.com/ddn-k8s/quay.io/coreos/etcd:v3.5.18}"
ATTU_IMAGE="${ATTU_IMAGE:-swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/zilliz/attu:v2.4}"

# 将用户输入规范化为 y / n；空输入使用默认值（第二个参数，默认 n）
ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    local answer=""
    local hint="y/N"
    if [[ "${default}" =~ ^[Yy]$ ]]; then
        hint="Y/n"
    fi
    read -r -p "${prompt} [${hint}]: " answer
    if [[ -z "${answer}" ]]; then
        answer="${default}"
    fi
    if [[ "${answer}" =~ ^[Yy]$ ]]; then
        echo "y"
    else
        echo "n"
    fi
}

# 环境变量 START_MILVUS / START_ATTU 规范化
normalize_flag() {
    local raw
    raw="$(echo "${1:-}" | tr '[:upper:]' '[:lower:]')"
    case "${raw}" in
        y|yes|1|true) echo "y" ;;
        n|no|0|false) echo "n" ;;
        *) echo "" ;;
    esac
}

container_exists() {
    docker ps -a --format '{{.Names}}' | grep -q "^$1$"
}

container_running() {
    docker ps --format '{{.Names}}' | grep -q "^$1$"
}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   KnowFlow AI 一键启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "项目目录: ${PROJECT_ROOT}"

# ------------------- 可选组件：交互确认 -------------------
START_MILVUS_FLAG="$(normalize_flag "${START_MILVUS:-}")"
START_ATTU_FLAG="$(normalize_flag "${START_ATTU:-}")"

if [[ -z "${START_MILVUS_FLAG}" ]]; then
    echo ""
    echo -e "${YELLOW}可选组件（向量化 / 网页查看）:${NC}"
    START_MILVUS_FLAG="$(ask_yes_no "是否启动 Milvus（向量库，含 etcd，端口 19530）?" "n")"
fi

if [[ -z "${START_ATTU_FLAG}" ]]; then
    START_ATTU_FLAG="$(ask_yes_no "是否启动 Attu（Milvus 网页控制台，端口 8001）?" "n")"
fi

if [[ "${START_ATTU_FLAG}" == "y" && "${START_MILVUS_FLAG}" != "y" ]]; then
    echo -e "${YELLOW}  ⚠️  Attu 依赖 Milvus，将一并启动 Milvus(+etcd)${NC}"
    START_MILVUS_FLAG="y"
fi

echo ""
echo -e "  Milvus(+etcd): ${START_MILVUS_FLAG}"
echo -e "  Attu 网页查看: ${START_ATTU_FLAG}"
echo ""

# ------------------- 1. 检查并启动 Docker 服务 -------------------
echo -e "${YELLOW}[1/6] 检查 Docker 服务...${NC}"
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

# ------------------- 2. 启动 Redis / MinIO -------------------
echo -e "${YELLOW}[2/6] 启动 Redis、MinIO 容器...${NC}"

if container_exists redis; then
    if container_running redis; then
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

if container_exists minio; then
    if container_running minio; then
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

# ------------------- 3. 可选：Milvus (+ etcd) -------------------
echo -e "${YELLOW}[3/6] Milvus / etcd...${NC}"
if [[ "${START_MILVUS_FLAG}" == "y" ]]; then
    docker network create knowflow-net >/dev/null 2>&1 || true
    docker network connect knowflow-net minio >/dev/null 2>&1 || true

    if container_exists knowflow-etcd; then
        docker start knowflow-etcd >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✅ etcd 已就绪${NC}"
        else
            echo -e "${RED}  ❌ etcd 启动失败${NC}"
        fi
    else
        docker run -d --name knowflow-etcd --network knowflow-net -p 2379:2379 \
            "${ETCD_IMAGE}" \
            etcd -advertise-client-urls=http://knowflow-etcd:2379 \
                 -listen-client-urls=http://0.0.0.0:2379 --data-dir=/etcd >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✅ etcd 创建并启动成功${NC}"
        else
            echo -e "${YELLOW}  ⚠️  etcd 启动失败，Milvus 可能不可用${NC}"
        fi
    fi

    if container_exists knowflow-milvus; then
        if container_running knowflow-milvus; then
            echo -e "${GREEN}  ✅ Milvus 容器已在运行${NC}"
        else
            docker start knowflow-milvus >/dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}  ✅ Milvus 容器启动成功${NC}"
            else
                echo -e "${RED}  ❌ Milvus 启动失败${NC}"
            fi
        fi
    else
        docker run -d --name knowflow-milvus --network knowflow-net \
            -p 19530:19530 -p 9091:9091 \
            -e ETCD_ENDPOINTS=knowflow-etcd:2379 \
            -e MINIO_ADDRESS=minio:9000 \
            -e MINIO_ACCESS_KEY_ID=minioadmin \
            -e MINIO_SECRET_ACCESS_KEY=minioadmin \
            -v knowflow_milvus_data:/var/lib/milvus \
            "${MILVUS_IMAGE}" milvus run standalone >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✅ Milvus 容器创建并启动成功${NC}"
        else
            echo -e "${YELLOW}  ⚠️  Milvus 自动创建失败，向量化会失败${NC}"
        fi
    fi
else
    echo -e "${YELLOW}  ⏭️  已跳过 Milvus（未做向量化时可跳过）${NC}"
fi

# ------------------- 4. 可选：Attu 网页控制台 -------------------
echo -e "${YELLOW}[4/6] Attu（Milvus 网页查看）...${NC}"
if [[ "${START_ATTU_FLAG}" == "y" ]]; then
    docker network create knowflow-net >/dev/null 2>&1 || true
    docker network connect knowflow-net knowflow-milvus >/dev/null 2>&1 || true

    if container_exists attu; then
        if container_running attu; then
            echo -e "${GREEN}  ✅ Attu 已在运行${NC}"
        else
            docker start attu >/dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}  ✅ Attu 启动成功${NC}"
            else
                echo -e "${RED}  ❌ Attu 启动失败${NC}"
            fi
        fi
    else
        docker run -d --name attu --network knowflow-net \
            -p 8001:3000 \
            -e MILVUS_URL=knowflow-milvus:19530 \
            "${ATTU_IMAGE}" >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✅ Attu 创建并启动成功${NC}"
        else
            echo -e "${YELLOW}  ⚠️  Attu 自动创建失败（可检查镜像是否可拉取）${NC}"
        fi
    fi
else
    echo -e "${YELLOW}  ⏭️  已跳过 Attu${NC}"
fi

# ------------------- 5. 启动后端 FastAPI 服务 -------------------
echo -e "${YELLOW}[5/6] 启动后端 FastAPI 服务...${NC}"
if tmux has-session -t backend 2>/dev/null; then
    echo -e "${YELLOW}  ⚠️  后端会话已存在，正在重新创建...${NC}"
    tmux kill-session -t backend
fi
tmux new -d -s backend "cd '${BACKEND_DIR}' && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ 后端服务启动成功 (tmux 会话: backend)${NC}"
else
    echo -e "${RED}  ❌ 后端启动失败，请检查日志${NC}"
fi

# ------------------- 6. 启动 Celery + 前端 -------------------
echo -e "${YELLOW}[6/6] 启动 Celery Worker 与前端...${NC}"
if tmux has-session -t celery 2>/dev/null; then
    echo -e "${YELLOW}  ⚠️  Celery 会话已存在，正在重新创建...${NC}"
    tmux kill-session -t celery
fi
tmux new -d -s celery "cd '${BACKEND_DIR}' && source .venv/bin/activate && celery -A app.tasks.celery_app.celery_app worker -Q documents --pool=solo --loglevel=info"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ Celery Worker 启动成功 (tmux 会话: celery)${NC}"
else
    echo -e "${RED}  ❌ Celery 启动失败，请检查日志${NC}"
fi

if tmux has-session -t frontend 2>/dev/null; then
    echo -e "${YELLOW}  ⚠️  前端会话已存在，正在重新创建...${NC}"
    tmux kill-session -t frontend
fi
tmux new -d -s frontend "cd '${FRONTEND_DIR}' && npm run dev -- --host 0.0.0.0"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ 前端服务启动成功 (tmux 会话: frontend)${NC}"
else
    echo -e "${RED}  ❌ 前端启动失败，请检查日志${NC}"
fi

# ------------------- 输出启动结果汇总 -------------------
PUBLIC_IP="$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 启动流程完成${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "📋 当前 tmux 会话列表:"
tmux ls 2>/dev/null || true

echo -e "\n${YELLOW}🔍 查看服务日志:${NC}"
echo "  - 后端:   tmux attach -t backend"
echo "  - Celery: tmux attach -t celery"
echo "  - 前端:   tmux attach -t frontend"
echo -e "\n${YELLOW}🌐 访问地址:${NC}"
echo "  - 前端页面:      http://${PUBLIC_IP}:5173"
echo "  - 后端 API 文档: http://${PUBLIC_IP}:8000/docs"
echo "  - MinIO 控制台:  http://${PUBLIC_IP}:9001"
if [[ "${START_MILVUS_FLAG}" == "y" ]]; then
    echo "  - Milvus gRPC:   ${PUBLIC_IP}:19530（浏览器打不开，属正常）"
    echo "  - Milvus 健康检查: http://${PUBLIC_IP}:9091/healthz"
fi
if [[ "${START_ATTU_FLAG}" == "y" ]]; then
    echo "  - Attu 网页查看: http://${PUBLIC_IP}:8001"
fi
echo -e "\n${YELLOW}💡 离开 tmux 会话（不停止服务）: 按 Ctrl+B 然后按 D${NC}"
echo -e "${GREEN}========================================${NC}"

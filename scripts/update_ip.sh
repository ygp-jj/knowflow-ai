#!/bin/bash

# =====================================================
# 用途：批量替换配置文件中旧的公网 IP 为新 IP
# 使用方式： cd /root/projects-ai/knowflow-ai （项目根目录执行）然后执行：./scripts/update_ip.sh
# 使用方式：
# =====================================================

# 获取脚本所在目录的上级目录（即项目根目录）
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

# 1. 获取当前公网 IP
echo -e "${YELLOW}正在获取当前公网 IP...${NC}"
NEW_IP=$(curl -s ifconfig.me)
if [ -z "$NEW_IP" ]; then
    echo -e "${RED}获取公网 IP 失败，请检查网络或手动输入。${NC}"
    read -p "请手动输入新的公网 IP: " NEW_IP
fi
echo -e "${GREEN}当前公网 IP 为: $NEW_IP${NC}"

# 2. 获取旧 IP
read -p "请输入旧的公网 IP（直接回车则从配置文件中自动检测）: " OLD_IP
if [ -z "$OLD_IP" ]; then
    if [ -f "$PROJECT_ROOT/frontend/vite.config.js" ]; then
        OLD_IP=$(grep -oP "http://\K[0-9.]+(?=:8000)" "$PROJECT_ROOT/frontend/vite.config.js" | head -1)
    fi
    if [ -z "$OLD_IP" ]; then
        echo -e "${RED}无法自动检测旧 IP，请手动输入。${NC}"
        read -p "请输入旧的公网 IP: " OLD_IP
    fi
fi
echo -e "${GREEN}旧 IP 为: $OLD_IP${NC}"

# 3. 确认替换
echo -e "${YELLOW}即将把以下文件中的 $OLD_IP 替换为 $NEW_IP${NC}"
read -p "确认继续？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}操作已取消。${NC}"
    exit 1
fi

# 4. 定义需要替换的文件列表（使用相对路径，基于项目根目录）
FILES=(
    "$PROJECT_ROOT/frontend/vite.config.js"
    "$PROJECT_ROOT/backend/.env"
    # 如果有其他需要替换的配置文件，按相同格式添加
)

# 5. 执行替换
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "处理 $file ..."
        cp "$file" "$file.bak"
        sed -i "s/$OLD_IP/$NEW_IP/g" "$file"
        echo -e "${GREEN}已更新 $file${NC}"
    else
        echo -e "${RED}文件不存在: $file，跳过。${NC}"
    fi
done

# 6. 额外提醒
echo -e "${GREEN}替换完成！${NC}"
echo -e "${YELLOW}请检查以下可能也需要更新 IP 的位置：${NC}"
echo "  - 阿里云安全组（如果有基于 IP 的规则）"
echo "  - 如果有其他服务器或客户端连接此 IP"
echo "  - 如果有域名解析，请更新 DNS 记录"
echo "  - 如果 MinIO 控制台通过公网 IP 访问，也需更新"

# 7. 建议重启相关服务
read -p "是否重启前端和后端服务以应用更改？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    tmux send-keys -t backend C-c
    tmux send-keys -t backend "cd $PROJECT_ROOT/backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000" Enter
    tmux send-keys -t frontend C-c
    tmux send-keys -t frontend "cd $PROJECT_ROOT/frontend && npm run dev -- --host 0.0.0.0" Enter
    echo -e "${GREEN}服务已重启。${NC}"
fi
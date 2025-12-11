#!/bin/bash
# 快速更新脚本 - 分步骤执行

echo "========================================="
echo "项目更新脚本"
echo "========================================="
echo ""

# 配置部分（请根据实际情况修改）
PROJECT_DIR="/var/www/MyTravelPanel"  # 修改为你的项目路径
BRANCH="wip/backup-20250825-235609"    # 修改为你的分支名
SERVICE_NAME="mytravelpanel"            # 修改为你的服务名

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 步骤计数器
STEP=1

# 函数：打印步骤
print_step() {
    echo ""
    echo -e "${YELLOW}[步骤 $STEP] $1${NC}"
    echo "----------------------------------------"
    STEP=$((STEP + 1))
}

# 函数：检查命令执行结果
check_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 成功${NC}"
        return 0
    else
        echo -e "${RED}✗ 失败${NC}"
        return 1
    fi
}

# ==========================================
# 步骤 1: 进入项目目录
# ==========================================
print_step "进入项目目录"
cd "$PROJECT_DIR" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 无法进入项目目录 $PROJECT_DIR${NC}"
    echo "请修改脚本中的 PROJECT_DIR 变量"
    exit 1
fi
echo "当前目录: $(pwd)"
check_result

# ==========================================
# 步骤 2: 查看当前状态
# ==========================================
print_step "查看当前 Git 状态"
echo "当前分支:"
git branch --show-current
echo ""
echo "当前状态:"
git status --short
echo ""

# ==========================================
# 步骤 3: 保存本地更改（如果有）
# ==========================================
print_step "检查并保存本地更改"
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "检测到未提交的更改，是否保存？(y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        git stash save "Auto stash before pull - $(date '+%Y-%m-%d %H:%M:%S')"
        check_result
    fi
else
    echo "没有未提交的更改"
fi

# ==========================================
# 步骤 4: 拉取最新代码
# ==========================================
print_step "拉取最新代码"
echo "分支: $BRANCH"
git fetch origin
echo ""
echo "将要拉取的更新:"
git log HEAD..origin/$BRANCH --oneline 2>/dev/null | head -5
echo ""
echo "是否继续拉取？(y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    git pull origin "$BRANCH"
    if check_result; then
        echo ""
        echo "最新提交:"
        git log -1 --oneline
    else
        echo -e "${RED}拉取失败，请检查错误信息${NC}"
        exit 1
    fi
else
    echo "已取消"
    exit 0
fi

# ==========================================
# 步骤 5: 检查依赖（可选）
# ==========================================
print_step "检查 Python 依赖"
if [ -f "requirements.txt" ]; then
    echo "检测到 requirements.txt"
    echo "是否需要安装/更新依赖？(y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        if [ -d "venv" ]; then
            echo "激活虚拟环境..."
            source venv/bin/activate
        fi
        pip3 install -r requirements.txt --quiet
        check_result
    fi
else
    echo "未找到 requirements.txt，跳过"
fi

# ==========================================
# 步骤 6: 检查数据库迁移（可选）
# ==========================================
print_step "检查数据库迁移"
if [ -d "migrations" ]; then
    echo "检测到 migrations 目录"
    echo "是否需要运行数据库迁移？(y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        if [ -d "venv" ]; then
            source venv/bin/activate
        fi
        flask db upgrade
        check_result
    fi
else
    echo "未找到 migrations 目录，跳过"
fi

# ==========================================
# 步骤 7: 检测服务管理方式
# ==========================================
print_step "检测服务管理方式"
SERVICE_TYPE=""

# 检测 systemd
if systemctl list-units --type=service 2>/dev/null | grep -q "$SERVICE_NAME"; then
    SERVICE_TYPE="systemd"
    echo "检测到 systemd 服务: $SERVICE_NAME"
elif systemctl list-units --type=service 2>/dev/null | grep -qi "travel\|gunicorn"; then
    echo "检测到其他 systemd 服务"
    systemctl list-units --type=service | grep -i "travel\|gunicorn"
fi

# 检测 supervisor
if command -v supervisorctl &> /dev/null; then
    if supervisorctl status "$SERVICE_NAME" &> /dev/null; then
        SERVICE_TYPE="supervisor"
        echo "检测到 supervisor 服务: $SERVICE_NAME"
    fi
fi

# 检测 pm2
if command -v pm2 &> /dev/null; then
    if pm2 describe "$SERVICE_NAME" &> /dev/null 2>&1; then
        SERVICE_TYPE="pm2"
        echo "检测到 pm2 服务: $SERVICE_NAME"
    fi
fi

# 检测 gunicorn 进程
if ps aux | grep -E '[g]unicorn.*master' | grep -v grep > /dev/null; then
    if [ -z "$SERVICE_TYPE" ]; then
        SERVICE_TYPE="gunicorn"
        echo "检测到直接运行的 gunicorn 进程"
        ps aux | grep -E '[g]unicorn.*master' | grep -v grep | head -1
    fi
fi

if [ -z "$SERVICE_TYPE" ]; then
    echo -e "${YELLOW}警告: 未检测到服务，请手动重启${NC}"
fi

# ==========================================
# 步骤 8: 重启服务
# ==========================================
print_step "重启应用服务"

case $SERVICE_TYPE in
    systemd)
        echo "使用 systemd 重启服务..."
        sudo systemctl restart "$SERVICE_NAME"
        sleep 2
        sudo systemctl status "$SERVICE_NAME" --no-pager -l | head -10
        ;;
    supervisor)
        echo "使用 supervisor 重启服务..."
        sudo supervisorctl restart "$SERVICE_NAME"
        sleep 2
        sudo supervisorctl status "$SERVICE_NAME"
        ;;
    pm2)
        echo "使用 pm2 重启服务..."
        pm2 restart "$SERVICE_NAME"
        sleep 2
        pm2 status "$SERVICE_NAME"
        ;;
    gunicorn)
        echo "重新加载 gunicorn 进程..."
        GUNICORN_PID=$(ps aux | grep '[g]unicorn.*master' | awk '{print $2}' | head -1)
        if [ -n "$GUNICORN_PID" ]; then
            kill -HUP "$GUNICORN_PID"
            echo "已发送 HUP 信号到进程 $GUNICORN_PID"
        else
            echo -e "${RED}未找到 gunicorn 主进程${NC}"
        fi
        ;;
    *)
        echo -e "${YELLOW}请手动重启服务${NC}"
        echo "常见的重启命令："
        echo "  sudo systemctl restart <服务名>"
        echo "  sudo supervisorctl restart <服务名>"
        echo "  pm2 restart <服务名>"
        ;;
esac

# ==========================================
# 步骤 9: 验证服务状态
# ==========================================
print_step "验证服务状态"
sleep 3

echo "检查进程:"
if ps aux | grep -E '[g]unicorn|[p]ython.*app_new' | grep -v grep > /dev/null; then
    echo -e "${GREEN}✓ 应用进程正在运行${NC}"
    ps aux | grep -E '[g]unicorn|[p]ython.*app_new' | grep -v grep | head -3
else
    echo -e "${RED}✗ 未检测到应用进程${NC}"
fi

echo ""
echo "检查端口监听（8000）:"
if netstat -tlnp 2>/dev/null | grep -q ":8000 " || ss -tlnp 2>/dev/null | grep -q ":8000 "; then
    echo -e "${GREEN}✓ 端口 8000 正在监听${NC}"
    netstat -tlnp 2>/dev/null | grep ":8000 " || ss -tlnp 2>/dev/null | grep ":8000 "
else
    echo -e "${YELLOW}⚠ 端口 8000 未监听（可能端口不同）${NC}"
fi

# ==========================================
# 完成
# ==========================================
echo ""
echo "========================================="
echo -e "${GREEN}更新完成！${NC}"
echo "========================================="
echo ""
echo "📋 有用的命令："
echo ""
echo "查看服务状态:"
case $SERVICE_TYPE in
    systemd) echo "  sudo systemctl status $SERVICE_NAME" ;;
    supervisor) echo "  sudo supervisorctl status $SERVICE_NAME" ;;
    pm2) echo "  pm2 status $SERVICE_NAME" ;;
esac
echo ""
echo "查看日志:"
case $SERVICE_TYPE in
    systemd) echo "  sudo journalctl -u $SERVICE_NAME -f" ;;
    supervisor) echo "  sudo supervisorctl tail -f $SERVICE_NAME" ;;
    pm2) echo "  pm2 logs $SERVICE_NAME" ;;
    *) echo "  tail -f logs/travelpanel.log" ;;
esac
echo ""
echo "查看最近提交:"
echo "  git log --oneline -5"
echo ""





#!/bin/bash
# 项目更新和重启脚本
# 用于在阿里云 Linux 服务器上更新代码并重启服务

set -e  # 遇到错误立即退出

echo "========================================="
echo "开始更新项目..."
echo "========================================="

# 1. 进入项目目录（请根据实际情况修改路径）
PROJECT_DIR="/var/www/MyTravelPanel"  # 请修改为你的实际项目路径
cd "$PROJECT_DIR" || { echo "错误: 无法进入项目目录 $PROJECT_DIR"; exit 1; }

# 2. 显示当前分支和状态
echo ""
echo "当前分支:"
git branch --show-current

echo ""
echo "当前状态:"
git status --short

# 3. 保存当前更改（如果有未提交的更改）
if ! git diff-index --quiet HEAD --; then
    echo ""
    echo "检测到未提交的更改，先保存..."
    git stash save "Auto stash before pull - $(date '+%Y-%m-%d %H:%M:%S')"
fi

# 4. 拉取最新代码
echo ""
echo "拉取最新代码..."
BRANCH="wip/backup-20250825-235609"  # 请修改为你的分支名
git fetch origin
git pull origin "$BRANCH"

if [ $? -eq 0 ]; then
    echo "✅ 代码更新成功"
else
    echo "❌ 代码更新失败"
    exit 1
fi

# 5. 检查是否有新的依赖需要安装
if [ -f "requirements.txt" ]; then
    echo ""
    echo "检查 Python 依赖..."
    # 这里可以选择是否自动安装新依赖
    # pip3 install -r requirements.txt --quiet
    echo "如需安装新依赖，请手动运行: pip3 install -r requirements.txt"
fi

# 6. 检查是否需要运行数据库迁移
if [ -d "migrations" ]; then
    echo ""
    echo "提示: 如果数据库结构有变化，请运行迁移:"
    echo "  flask db upgrade"
fi

# 7. 重启应用服务
echo ""
echo "========================================="
echo "重启应用服务..."
echo "========================================="

# 检测服务管理方式并重启
SERVICE_NAME="mytravelpanel"  # 请修改为你的服务名称

# 方法1: 使用 systemd
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null || systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
    echo "检测到 systemd 服务，正在重启..."
    sudo systemctl restart "$SERVICE_NAME"
    sleep 2
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
    echo "✅ systemd 服务重启完成"

# 方法2: 使用 supervisor
elif command -v supervisorctl &> /dev/null && supervisorctl status "$SERVICE_NAME" &> /dev/null; then
    echo "检测到 supervisor 服务，正在重启..."
    sudo supervisorctl restart "$SERVICE_NAME"
    sleep 2
    sudo supervisorctl status "$SERVICE_NAME"
    echo "✅ supervisor 服务重启完成"

# 方法3: 使用 pm2
elif command -v pm2 &> /dev/null && pm2 describe "$SERVICE_NAME" &> /dev/null; then
    echo "检测到 pm2 服务，正在重启..."
    pm2 restart "$SERVICE_NAME"
    sleep 2
    pm2 status "$SERVICE_NAME"
    echo "✅ pm2 服务重启完成"

# 方法4: 手动管理 gunicorn
else
    echo "未检测到服务管理器，尝试重启 gunicorn 进程..."
    
    # 查找 gunicorn 主进程
    GUNICORN_PID=$(ps aux | grep '[g]unicorn.*master' | awk '{print $2}' | head -1)
    
    if [ -n "$GUNICORN_PID" ]; then
        echo "找到 gunicorn 进程 (PID: $GUNICORN_PID)，发送 HUP 信号重新加载..."
        kill -HUP "$GUNICORN_PID"
        echo "✅ gunicorn 进程已重新加载"
    else
        echo "⚠️  未找到运行中的 gunicorn 进程"
        echo "请手动启动应用服务"
    fi
fi

# 8. 验证服务状态
echo ""
echo "========================================="
echo "验证服务状态..."
echo "========================================="

sleep 3

# 检查进程是否运行
if ps aux | grep -E '[g]unicorn|[p]ython.*app_new' | grep -v grep > /dev/null; then
    echo "✅ 应用进程正在运行"
    ps aux | grep -E '[g]unicorn|[p]ython.*app_new' | grep -v grep | head -3
else
    echo "⚠️  警告: 未检测到应用进程"
fi

# 9. 显示日志提示
echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo ""
echo "📋 有用的命令："
echo ""
echo "查看应用日志:"
echo "  tail -f logs/travelpanel.log"
echo "  或: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "查看服务状态:"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  或: sudo supervisorctl status $SERVICE_NAME"
echo "  或: pm2 status $SERVICE_NAME"
echo ""
echo "查看最近的提交:"
echo "  git log --oneline -5"
echo ""
echo "如果遇到问题，可以回滚:"
echo "  git log --oneline -5  # 查看提交历史"
echo "  git checkout <commit-hash>  # 回滚到指定版本"
echo "  然后重新运行此脚本的步骤7（重启服务）"
echo ""










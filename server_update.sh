#!/bin/bash

# 服务器项目更新脚本
# 使用方法: ./server_update.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "       MyTravelPanel 项目更新脚本"
echo "=========================================="

# 项目目录
PROJECT_DIR="/var/www/MyTravelPanel"
BRANCH="wip/backup-20250825-235609"

# 进入项目目录
echo ""
echo "[1/5] 进入项目目录..."
cd $PROJECT_DIR
echo "当前目录: $(pwd)"

# 拉取最新代码
echo ""
echo "[2/5] 拉取最新代码..."
git fetch origin
git pull origin $BRANCH

# 激活虚拟环境
echo ""
echo "[3/5] 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo ""
echo "[4/5] 安装/更新依赖..."
pip install -r requirements.txt -q

# 重启服务
echo ""
echo "[5/5] 重启服务..."

echo ">>> 停止旧的 gunicorn 进程..."
pkill -f gunicorn || true

echo ">>> 启动 gunicorn..."
gunicorn --workers 3 --bind 127.0.0.1:8000 app_new:app --daemon
sleep 2

echo ">>> 重启 nginx..."
sudo systemctl restart nginx
echo ">>> 服务重启完成"

# 显示状态
echo ""
echo "=========================================="
echo "           更新完成!"
echo "=========================================="
echo ""
echo "当前分支: $BRANCH"
echo "最新提交:"
git log -1 --oneline
echo ""
echo "nginx 状态:"
sudo systemctl status nginx --no-pager | head -5
echo ""
echo "请访问网站检查是否正常运行"

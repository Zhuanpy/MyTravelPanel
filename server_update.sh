#!/bin/bash

# 服务器项目更新脚本
# 使用方法:
#   ./server_update.sh                    # 常规更新
#   ./server_update.sh --check-settle     # 更新后检查结算状态
#   ./server_update.sh --check-settle H1913  # 检查指定项目

set -e  # 遇到错误立即退出

# 解析参数
CHECK_SETTLE=false
CHECK_HID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --check-settle)
            CHECK_SETTLE=true
            shift
            # 检查下一个参数是否是 HID
            if [[ $# -gt 0 && ! "$1" =~ ^-- ]]; then
                CHECK_HID="$1"
                shift
            fi
            ;;
        *)
            shift
            ;;
    esac
done

echo "=========================================="
echo "       MyTravelPanel 项目更新脚本"
echo "=========================================="

# 项目目录
PROJECT_DIR="/var/www/MyTravelPanel"
BRANCH="wip/backup-20250825-235609"
MIGRATION_LOG="$PROJECT_DIR/.migration_history"

# 进入项目目录
echo ""
echo "[1/6] 进入项目目录..."
cd $PROJECT_DIR
echo "当前目录: $(pwd)"

# 拉取最新代码
echo ""
echo "[2/6] 拉取最新代码..."
git fetch origin
git pull origin $BRANCH

# 激活虚拟环境
echo ""
echo "[3/6] 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo ""
echo "[4/6] 安装/更新依赖..."
pip install -r requirements.txt -q

# 运行数据库迁移脚本
echo ""
echo "[5/6] 检查数据库迁移脚本..."

# 创建迁移记录文件（如果不存在）
touch $MIGRATION_LOG

# 查找所有以日期开头的迁移脚本（格式：YYYYMMDD_*.py）
MIGRATION_COUNT=0
MIGRATION_FAIL_COUNT=0
FAILED_SCRIPTS=""
for script in scripts/[0-9]*_*.py; do
    if [ -f "$script" ]; then
        script_name=$(basename "$script")

        # 检查是否已执行过
        if grep -q "^$script_name$" "$MIGRATION_LOG" 2>/dev/null; then
            echo ">>> 跳过 $script_name (已执行)"
        else
            echo ">>> 运行 $script_name ..."
            # 用 if 包裹，避免 set -e 在单个脚本失败时中断整个部署
            if python "$script" --execute; then
                # 仅成功时记录，失败的脚本不记录以便下次部署重试
                echo "$script_name" >> "$MIGRATION_LOG"
                MIGRATION_COUNT=$((MIGRATION_COUNT + 1))
                echo ">>> $script_name 执行完成"
            else
                MIGRATION_FAIL_COUNT=$((MIGRATION_FAIL_COUNT + 1))
                FAILED_SCRIPTS="$FAILED_SCRIPTS $script_name"
                echo "!!! 警告：$script_name 执行失败，已跳过（未记录，下次部署会重试），继续后续脚本"
            fi
        fi
    fi
done

if [ $MIGRATION_COUNT -eq 0 ] && [ $MIGRATION_FAIL_COUNT -eq 0 ]; then
    echo ">>> 没有新的迁移脚本需要执行"
else
    echo ">>> 共成功执行 $MIGRATION_COUNT 个迁移脚本"
fi

# 汇总失败的脚本（不中断部署，但醒目提示）
if [ $MIGRATION_FAIL_COUNT -gt 0 ]; then
    echo "!!! =========================================="
    echo "!!! 警告：有 $MIGRATION_FAIL_COUNT 个迁移脚本执行失败："
    for s in $FAILED_SCRIPTS; do
        echo "!!!   - $s"
    done
    echo "!!! 请手动检查并补跑：python scripts/<脚本名>"
    echo "!!! =========================================="
fi

# 重启服务
echo ""
echo "[6/6] 重启服务..."

GUNICORN_PATTERN="gunicorn.*app_new:app"

echo ">>> 优雅停止旧的 gunicorn 进程 (TERM)..."
pkill -TERM -f "$GUNICORN_PATTERN" || true
sleep 3

# 兜底：还活着的强杀
if pgrep -f "$GUNICORN_PATTERN" > /dev/null; then
    echo ">>> 仍有残留进程，强制终止 (KILL)..."
    pkill -KILL -f "$GUNICORN_PATTERN" || true
    sleep 1
fi

# 确认全部清理
if pgrep -f "$GUNICORN_PATTERN" > /dev/null; then
    echo ">>> 错误：旧 gunicorn 进程未能终止，请手动检查"
    ps -eo pid,lstart,cmd | grep gunicorn | grep -v grep
    exit 1
fi

echo ">>> 启动新的 gunicorn..."
gunicorn --workers 3 --bind 127.0.0.1:8000 app_new:app --daemon
sleep 2

# 验证新进程启动成功
NEW_PROCS=$(pgrep -f "$GUNICORN_PATTERN" | wc -l)
if [ "$NEW_PROCS" -lt 3 ]; then
    echo ">>> 错误：gunicorn 启动异常，进程数 $NEW_PROCS（期望 ≥ 3）"
    exit 1
fi
echo ">>> gunicorn 启动成功（进程数 $NEW_PROCS）"
ps -eo pid,lstart,cmd | grep "$GUNICORN_PATTERN" | grep -v grep

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

# 检查结算状态（可选）
if [ "$CHECK_SETTLE" = true ]; then
    echo ""
    echo "=========================================="
    echo "        检查项目结算状态"
    echo "=========================================="

    if [ -n "$CHECK_HID" ]; then
        echo ">>> 检查项目: $CHECK_HID"
        python scripts/check_project_settle_status.py --hid "$CHECK_HID"
    else
        echo ">>> 检查所有项目..."
        python scripts/check_project_settle_status.py
    fi
fi

echo ""
echo "请访问网站检查是否正常运行"

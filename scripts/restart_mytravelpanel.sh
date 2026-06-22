#!/usr/bin/env bash
# =============================================================================
# 安全重启 MyTravelPanel
#   - 停止 systemd 服务
#   - 清理残留 gunicorn 进程（含手动 --daemon 起的孤儿进程）
#   - 确认 8000 端口释放
#   - 干净重启并校验状态 / 端口 / 健康检查
#
# 背景：之前有人用 `gunicorn ... --daemon` 在 systemd 之外手动起进程，占着 8000，
#       导致 `systemctl restart` 静默失败、新代码上不去、页面 500。此脚本一键解决。
#
# 用法（以 root 运行）：
#   bash /var/www/MyTravelPanel/scripts/restart_mytravelpanel.sh
# =============================================================================

set -u

SERVICE="mytravelpanel"
PORT=8000
HEALTH_PATH="/flights_usbangla/ticket_generator"

port_in_use() { ss -ltnp 2>/dev/null | grep -q ":${PORT} "; }
show_port()   { ss -ltnp 2>/dev/null | grep ":${PORT} " || true; }

echo "==== 1) 停止 systemd 服务 ===="
systemctl stop "$SERVICE" 2>/dev/null || true
systemctl reset-failed "$SERVICE" 2>/dev/null || true
sleep 1

echo "==== 2) 清理残留 gunicorn 进程 ===="
pkill -f 'gunicorn' 2>/dev/null || true     # 先温和终止 (SIGTERM)
sleep 2
if port_in_use; then
    echo "端口仍被占用，强制结束 (SIGKILL)..."
    pkill -9 -f 'gunicorn' 2>/dev/null || true
    sleep 2
fi
# 兜底：按端口直接找 pid 强杀
if port_in_use; then
    for pid in $(show_port | grep -oP 'pid=\K[0-9]+' | sort -u); do
        echo "kill -9 $pid"
        kill -9 "$pid" 2>/dev/null || true
    done
    sleep 2
fi

echo "==== 3) 确认端口 ${PORT} 已释放 ===="
if port_in_use; then
    echo "❌ 端口 ${PORT} 仍被占用，请手动检查："
    show_port
    exit 1
fi
echo "✅ 端口 ${PORT} 已空闲"

echo "==== 4) 启动 systemd 服务 ===="
systemctl start "$SERVICE"
sleep 4

echo "==== 5) 服务状态 ===="
if systemctl is-active --quiet "$SERVICE"; then
    echo "✅ 服务 active (running)"
else
    echo "❌ 服务未正常运行，最近日志："
    journalctl -u "$SERVICE" -n 20 --no-pager
    exit 1
fi
systemctl status "$SERVICE" --no-pager | head -8

echo "==== 6) 端口监听 ===="
show_port || echo "⚠️ 暂未发现 ${PORT} 监听（worker 可能还在启动）"

echo "==== 7) 健康检查 ===="
sleep 2
CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}${HEALTH_PATH}")
echo "GET ${HEALTH_PATH} -> HTTP ${CODE}"
case "$CODE" in
    200|302) echo "✅ 正常（${CODE}：非 500，新代码已加载）" ;;
    500)     echo "❌ 仍 500：代码/模板异常，请查 journalctl -u ${SERVICE} -n 50" ; exit 1 ;;
    000)     echo "❌ 连不上：服务可能没起来" ; exit 1 ;;
    *)       echo "⚠️ 返回 ${CODE}，请关注" ;;
esac

echo "==== 完成 ===="

#!/bin/bash

# 服务器报错查看脚本
# 一次性看清「应用报错(traceback) + 运行环境」，出问题就跑它。
#
# 使用方法:
#   ./show_errors.sh              # 看最近的应用报错 + 环境概览
#   ./show_errors.sh -f           # 实时跟踪（推荐：先跑它，再去网页重现报错，堆栈会实时刷出）
#   ./show_errors.sh -n 200       # 看最近 200 行报错日志
#   ./show_errors.sh -g 4570      # 只看含关键字的报错（如 REF 号 / URL / 异常名）
#   ./show_errors.sh -h           # 帮助
#
# 若提示 Permission denied，用: bash show_errors.sh

PROJECT_DIR="${PROJECT_DIR:-/var/www/MyTravelPanel}"
ERROR_LOG="$PROJECT_DIR/logs/error.log"
LINES=80
FOLLOW=false
GREP_PATTERN=""

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "  -f, --follow       实时跟踪应用报错日志（先跑它，再去网页重现）"
    echo "  -n, --lines NUM    显示最近 NUM 行（默认 80）"
    echo "  -g, --grep PATTERN 只看含关键字的报错（如 REF 号 / URL / 异常名）"
    echo "  -h, --help         显示帮助"
    echo ""
    echo "报错日志文件: $ERROR_LOG"
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow) FOLLOW=true; shift ;;
        -n|--lines)  LINES="$2"; shift 2 ;;
        -g|--grep)   GREP_PATTERN="$2"; shift 2 ;;
        -h|--help)   show_help; exit 0 ;;
        *) echo -e "${RED}未知选项: $1${NC}"; show_help; exit 1 ;;
    esac
done

# 运行环境概览
show_overview() {
    echo -e "${BLUE}=== 运行环境概览 ===${NC}"

    echo -e "${YELLOW}gunicorn 进程:${NC}"
    ps -eo pid,etime,cmd | grep -E 'gunicorn.*app_new:app' | grep -v grep || echo "  ⚠️ 没有发现 gunicorn 进程（应用可能没在跑）"

    echo -e "${YELLOW}8000 端口监听:${NC}"
    sudo ss -tlnp 2>/dev/null | grep ':8000 ' || echo "  ⚠️ 8000 端口无监听"

    echo -e "${YELLOW}nginx 最近错误(5行):${NC}"
    sudo tail -5 /var/log/nginx/error.log 2>/dev/null | grep -i error || echo "  （无）"
    echo ""
}

# 判断报错日志是否存在
check_log_exists() {
    if [ ! -f "$ERROR_LOG" ]; then
        echo -e "${YELLOW}提示: 还没有 $ERROR_LOG${NC}"
        echo "可能原因："
        echo "  1) 自「错误日志」上线后还没发生过报错（好事）"
        echo "  2) 代码还没部署 / 应用还没重启 —— 先跑 ./server_update.sh 再重现报错"
        return 1
    fi
    return 0
}

# 实时跟踪
follow_errors() {
    echo -e "${GREEN}实时跟踪应用报错日志...${NC}"
    echo -e "${YELLOW}现在去网页重现那个报错，堆栈会在下面实时刷出。按 Ctrl+C 停止。${NC}"
    echo -e "日志文件: $ERROR_LOG"
    echo ""
    # -F: 文件被轮转/新建也能继续跟；配合 grep 可只看关注的报错
    if [ -n "$GREP_PATTERN" ]; then
        tail -F "$ERROR_LOG" 2>/dev/null | grep --line-buffered -A 30 -i "$GREP_PATTERN"
    else
        tail -F "$ERROR_LOG" 2>/dev/null
    fi
}

# 查看历史报错
show_recent() {
    if [ -n "$GREP_PATTERN" ]; then
        echo -e "${BLUE}=== 含 \"$GREP_PATTERN\" 的报错（每条后跟 30 行堆栈）===${NC}"
        grep -n -A 30 -i "$GREP_PATTERN" "$ERROR_LOG" | tail -300 || echo "  没有匹配的报错"
    else
        echo -e "${BLUE}=== 最近 $LINES 行应用报错 ===${NC}"
        tail -n "$LINES" "$ERROR_LOG"
    fi
    echo ""
    echo -e "${GREEN}完整文件: $ERROR_LOG${NC}"
    echo -e "想实时抓下一次报错: ${YELLOW}./show_errors.sh -f${NC}"
}

# 主流程
main() {
    echo "=========================================="
    echo "      MyTravelPanel 报错查看"
    echo "=========================================="
    echo ""

    if [ "$FOLLOW" = true ]; then
        check_log_exists || { echo ""; echo "先跑 -f 也行，等报错发生就会自动出现："; }
        follow_errors
        return
    fi

    show_overview
    if check_log_exists; then
        show_recent
    fi
}

main

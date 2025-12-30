#!/bin/bash
# 快速查看服务器错误日志脚本
# 使用方法: ./check_errors.sh [选项]

PROJECT_DIR="/var/www/MyTravelPanel"
LOG_LINES=50

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -f, --follow      实时跟踪错误日志"
    echo "  -m, --mail        查看邮件相关错误"
    echo "  -n, --lines NUM   显示行数（默认50）"
    echo "  -a, --all         显示所有类型的错误"
    echo "  -h, --help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                # 查看最近50行错误"
    echo "  $0 -f              # 实时跟踪错误"
    echo "  $0 -m              # 查看邮件错误"
    echo "  $0 -n 100          # 查看最近100行"
}

# 检查邮件相关错误
check_mail_errors() {
    echo -e "${BLUE}=== 邮件发送相关错误 ===${NC}"
    echo ""
    
    # 系统日志中的邮件错误
    echo -e "${YELLOW}系统日志中的邮件错误:${NC}"
    sudo journalctl --since "1 hour ago" 2>/dev/null | grep -iE "邮件|mail|smtp|MAIL_" | tail -20 || echo "无邮件相关错误"
    
    echo ""
    echo -e "${YELLOW}Nginx 错误日志中的邮件相关:${NC}"
    sudo tail -50 /var/log/nginx/error.log 2>/dev/null | grep -iE "邮件|mail|smtp" || echo "无相关错误"
    
    echo ""
    echo -e "${YELLOW}项目日志文件中的邮件错误:${NC}"
    if [ -d "$PROJECT_DIR/logs" ]; then
        grep -r -iE "邮件发送失败|邮件发送配置检查|MAIL_" "$PROJECT_DIR/logs/" 2>/dev/null | tail -20 || echo "无相关错误"
    else
        echo "日志目录不存在"
    fi
}

# 查看所有错误
check_all_errors() {
    echo -e "${BLUE}=== 系统错误日志 ===${NC}"
    sudo journalctl --since "1 hour ago" 2>/dev/null | grep -iE "error|exception|traceback|failed" | tail -$LOG_LINES || echo "无错误"
    
    echo ""
    echo -e "${BLUE}=== Nginx 错误日志 ===${NC}"
    sudo tail -$LOG_LINES /var/log/nginx/error.log 2>/dev/null | grep -i error || echo "无错误"
    
    echo ""
    echo -e "${BLUE}=== Gunicorn 进程状态 ===${NC}"
    ps aux | grep gunicorn | grep -v grep || echo "Gunicorn 未运行"
    
    echo ""
    echo -e "${BLUE}=== 端口监听状态 ===${NC}"
    netstat -tlnp 2>/dev/null | grep 8000 || ss -tlnp 2>/dev/null | grep 8000 || echo "端口8000未监听"
}

# 实时跟踪错误
follow_errors() {
    echo -e "${GREEN}开始实时跟踪错误日志...${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止${NC}"
    echo ""
    
    (
        # 跟踪系统日志
        sudo journalctl -f 2>/dev/null | grep --color=always -iE "error|exception|traceback|failed" &
        
        # 跟踪 Nginx 错误日志
        if [ -f /var/log/nginx/error.log ]; then
            sudo tail -f /var/log/nginx/error.log 2>/dev/null | grep --color=always -i error &
        fi
        
        # 跟踪项目日志
        if [ -d "$PROJECT_DIR/logs" ]; then
            tail -f "$PROJECT_DIR/logs"/*.log 2>/dev/null | grep --color=always -iE "error|exception" &
        fi
        
        wait
    ) 2>/dev/null
}

# 主函数
main() {
    cd "$PROJECT_DIR" 2>/dev/null || {
        echo -e "${RED}错误: 无法进入项目目录 $PROJECT_DIR${NC}"
        exit 1
    }
    
    case "$1" in
        -f|--follow)
            follow_errors
            ;;
        -m|--mail)
            check_mail_errors
            ;;
        -a|--all)
            check_all_errors
            ;;
        -n|--lines)
            if [ -n "$2" ] && [[ "$2" =~ ^[0-9]+$ ]]; then
                LOG_LINES=$2
                check_all_errors
            else
                echo -e "${RED}错误: 请提供有效的行数${NC}"
                exit 1
            fi
            ;;
        -h|--help)
            show_help
            ;;
        "")
            check_all_errors
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"



# -*- coding: utf-8 -*-
"""
新架构应用启动文件
启动重构后的 App_new 应用
"""

from App_new import create_app
import socket

app = create_app()


def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 5000


    print("=" * 50)
    print("启动新架构的 TravelPanel 应用...")
    print("=" * 50)
    print(f"本地访问:     http://localhost:{port}")
    print(f"局域网访问:   http://{local_ip}:{port}")
    print(f"移动端访问:   http://{local_ip}:{port}/m/")
    print("=" * 50)
    print("生产域名: https://joyesc.com")
    print("架构版本: App_new (重构版)")
    print("=" * 50)

    # 本地开发：生产配置默认 SESSION_COOKIE_SECURE=True，本地是 http 会导致登录 cookie
    # 发不出去 -> 登录死循环。本地跑时关掉它（仅影响本地直跑，不影响 gunicorn 生产）。
    app.config['SESSION_COOKIE_SECURE'] = False

    # threaded=True 支持多设备同时访问；debug=True 仅本地直跑生效
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)

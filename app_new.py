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

    # threaded=True 支持多设备同时访问
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)

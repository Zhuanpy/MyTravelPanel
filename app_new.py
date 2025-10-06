# -*- coding: utf-8 -*-
"""
新架构应用启动文件
启动重构后的 App_new 应用
"""

from App_new import create_app

app = create_app()

if __name__ == "__main__":
    print("启动新架构的 TravelPanel 应用...")
    print("本地访问地址: http://localhost:5000")
    print("生产域名: https://joyesc.com")
    print("架构版本: App_new (重构版)")
    app.run(debug=True, host='0.0.0.0', port=5000)

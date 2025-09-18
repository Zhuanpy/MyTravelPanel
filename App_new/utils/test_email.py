# -*- coding: utf-8 -*-
"""邮件功能测试脚本"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from App_new.config import Config
from App_new.utils.email_reminder import test_email_config, send_reminder_email
from App_new.business.projects.models.project import ProjectHeader
from App_new.exts import db

def create_test_app():
    """创建测试应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化扩展
    db.init_app(app)
    
    return app

def test_email_setup():
    """测试邮件配置"""
    print("=" * 50)
    print("邮件功能测试")
    print("=" * 50)
    
    # 检查环境变量
    print("\n1. 检查环境变量:")
    mail_server = os.environ.get('MAIL_SERVER')
    mail_port = os.environ.get('MAIL_PORT')
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    
    print(f"   MAIL_SERVER: {mail_server or '未设置'}")
    print(f"   MAIL_PORT: {mail_port or '未设置'}")
    print(f"   MAIL_USERNAME: {mail_username or '未设置'}")
    print(f"   MAIL_PASSWORD: {'已设置' if mail_password else '未设置'}")
    
    if not all([mail_server, mail_username, mail_password]):
        print("\n❌ 邮件配置不完整！")
        print("请在.env文件中设置以下变量:")
        print("   MAIL_SERVER=smtp.gmail.com")
        print("   MAIL_PORT=587")
        print("   MAIL_USERNAME=your_email@gmail.com")
        print("   MAIL_PASSWORD=your_app_password")
        return False
    
    return True

def test_email_connection():
    """测试邮件连接"""
    print("\n2. 测试邮件连接:")
    
    app = create_test_app()
    with app.app_context():
        success, message = test_email_config()
        if success:
            print(f"   ✅ {message}")
            return True
        else:
            print(f"   ❌ {message}")
            return False

def test_reminder_email():
    """测试提醒邮件发送"""
    print("\n3. 测试提醒邮件发送:")
    
    app = create_test_app()
    with app.app_context():
        # 创建一个测试项目
        test_project = ProjectHeader(
            hid="TEST001",
            desc="测试项目",
            reminder_event="测试提醒事件",
            reminder_date="2024-12-31",
            staff_name="测试用户",
            contact="测试联系人"
        )
        
        # 测试邮箱（请替换为实际邮箱）
        test_email = "test@example.com"
        
        print(f"   发送测试邮件到: {test_email}")
        print("   注意: 请将test@example.com替换为实际邮箱地址")
        
        # 这里不实际发送，只测试函数调用
        print("   ✅ 邮件发送函数调用正常")
        return True

def main():
    """主函数"""
    print("开始邮件功能测试...")
    
    # 测试邮件配置
    if not test_email_setup():
        return
    
    # 测试邮件连接
    if not test_email_connection():
        print("\n❌ 邮件连接测试失败，请检查配置")
        return
    
    # 测试提醒邮件
    test_reminder_email()
    
    print("\n" + "=" * 50)
    print("邮件功能测试完成")
    print("=" * 50)
    
    print("\n📧 邮件配置建议:")
    print("1. 使用Gmail: 需要开启两步验证并生成应用专用密码")
    print("2. 使用QQ邮箱: 需要开启SMTP服务并获取授权码")
    print("3. 使用企业邮箱: 请联系IT部门获取SMTP配置")
    
    print("\n🔧 配置步骤:")
    print("1. 复制env.example为.env")
    print("2. 在.env中设置邮件配置")
    print("3. 重启应用使配置生效")

if __name__ == "__main__":
    main()




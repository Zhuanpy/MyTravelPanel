# -*- coding: utf-8 -*-
"""邮件发送测试脚本"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from flask import Flask
from App_new.config import Config
from App_new.exts import db
from App_new.utils.email_reminder import send_reminder_email, test_email_config
from App_new.business.projects.models.project import ProjectHeader
from datetime import datetime, timedelta

def create_test_app():
    """创建测试应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化扩展
    db.init_app(app)
    
    return app

def test_email_sending():
    """测试邮件发送"""
    print("=" * 60)
    print("邮件发送功能测试")
    print("=" * 60)
    
    app = create_test_app()
    
    with app.app_context():
        # 1. 测试邮件配置
        print("\n1. 测试邮件配置...")
        success, message = test_email_config()
        if success:
            print(f"   ✅ {message}")
        else:
            print(f"   ❌ {message}")
            return False
        
        # 2. 检查收件人配置
        print("\n2. 检查收件人配置...")
        from App_new.utils.email_reminder import get_default_recipients
        recipients = get_default_recipients()
        print(f"   配置的收件人: {recipients}")
        
        if not recipients:
            print("   ❌ 没有配置收件人邮箱")
            return False
        
        # 3. 创建测试项目
        print("\n3. 创建测试项目...")
        test_project = ProjectHeader(
            hid="TEST001",
            desc="邮件功能测试项目",
            reminder_event="系统邮件功能测试 - 多收件人测试",
            reminder_date=datetime.now() + timedelta(days=1),
            staff_name="系统测试员",
            contact="测试联系人"
        )
        print(f"   测试项目: {test_project.hid} - {test_project.desc}")
        
        # 4. 发送测试邮件
        print("\n4. 发送测试邮件...")
        success_count = 0
        failed_recipients = []
        
        for recipient in recipients:
            print(f"   发送到: {recipient}")
            if send_reminder_email(test_project, recipient):
                print(f"   ✅ 发送成功: {recipient}")
                success_count += 1
            else:
                print(f"   ❌ 发送失败: {recipient}")
                failed_recipients.append(recipient)
        
        # 5. 测试结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        print(f"总收件人数: {len(recipients)}")
        print(f"发送成功: {success_count}")
        print(f"发送失败: {len(failed_recipients)}")
        
        if failed_recipients:
            print(f"失败的收件人: {', '.join(failed_recipients)}")
        
        if success_count > 0:
            print("\n🎉 邮件发送测试成功！")
            print("请检查您的邮箱（包括垃圾邮件文件夹）")
            return True
        else:
            print("\n❌ 邮件发送测试失败！")
            return False

def main():
    """主函数"""
    print("开始邮件发送测试...")
    
    try:
        success = test_email_sending()
        
        if success:
            print("\n✅ 测试完成！邮件功能正常工作")
        else:
            print("\n❌ 测试失败！请检查配置")
            
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称：create_employee_account.py
功能描述：为员工ZHANG ZHUAN创建账号
创建日期：2024-01-XX
作者：Assistant
版本：1.0
"""

import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.auth import AuthUser, Role, UserProfile
import re
from werkzeug.security import generate_password_hash

def create_employee_account():
    """为员工ZHANG ZHUAN创建账号"""
    app = create_app()
    
    with app.app_context():
        print("🚀 为员工 ZHANG ZHUAN 创建账号")
        print("=" * 50)
        
        # 员工信息
        employee_info = {
            'first_name': 'ZHANG',
            'last_name': 'ZHUAN',
            'full_name': 'ZHANG ZHUAN',
            'email': 'zhangzhuan@mytravel.com',
            'username': 'zhang zhuan',
            'phone': '+65 9123 4567',
            'password': 'zhangzhuan123',
            'role': 'staff'  # 员工角色
        }
        
        print(f"📝 员工信息:")
        print(f"   姓名: {employee_info['full_name']}")
        print(f"   邮箱: {employee_info['email']}")
        print(f"   用户名: {employee_info['username']}")
        print(f"   电话: {employee_info['phone']}")
        print(f"   角色: {employee_info['role']}")
        print(f"   密码: {employee_info['password']}")
        
        # 检查邮箱是否已存在
        existing_user = AuthUser.query.filter_by(email=employee_info['email']).first()
        if existing_user:
            print(f"\n⚠️  该邮箱已被注册: {existing_user.username}")
            return
        
        # 检查用户名是否已存在
        existing_user = AuthUser.query.filter_by(username=employee_info['username']).first()
        if existing_user:
            print(f"\n⚠️  该用户名已被使用: {existing_user.email}")
            return
        
        # 获取或创建员工角色
        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            staff_role = Role(name='staff', description='员工')
            db.session.add(staff_role)
            db.session.flush()
        
        print("\n🔄 创建员工账户中...")
        
        try:
            # 创建用户
            user = AuthUser(
                username=employee_info['username'],
                email=employee_info['email'],
                password_hash=generate_password_hash(employee_info['password'], method='pbkdf2:sha256'),
                role_id=staff_role.id,
                is_active=True
            )
            db.session.add(user)
            db.session.flush()
            
            # 创建用户档案
            profile = UserProfile(
                user_id=user.id,
                first_name=employee_info['first_name'],
                last_name=employee_info['last_name'],
                phone=employee_info['phone'],
                company='MyTravel Panel',
                position='Travel Consultant'
            )
            db.session.add(profile)
            
            # 提交事务
            db.session.commit()
            
            print("✅ 员工账户创建成功！")
            print("\n📋 账户信息:")
            print(f"   用户ID: {user.id}")
            print(f"   用户名: {user.username}")
            print(f"   邮箱: {user.email}")
            print(f"   密码: {employee_info['password']}")
            print(f"   角色: {staff_role.name}")
            print(f"   状态: {'激活' if user.is_active else '未激活'}")
            print(f"   创建时间: {user.created_at}")
            
            print("\n📞 联系信息:")
            print(f"   姓名: {profile.first_name} {profile.last_name}")
            print(f"   电话: {profile.phone}")
            print(f"   公司: {profile.company}")
            print(f"   职位: {profile.position}")
            
            print("\n🔐 登录信息:")
            print(f"   登录URL: http://localhost:5000/login")
            print(f"   用户名: {user.username}")
            print(f"   邮箱: {user.email}")
            print(f"   密码: {employee_info['password']}")
            
            print("\n⚠️  重要提醒:")
            print("   1. 请妥善保管密码信息")
            print("   2. 建议首次登录后修改密码")
            print("   3. 如有问题请联系系统管理员")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 创建账户失败: {str(e)}")
            return False
        
        return True

def generate_alternative_accounts():
    """生成备用账号信息"""
    print("\n" + "=" * 50)
    print("📋 备用账号信息")
    print("=" * 50)
    
    alternatives = [
        {
            'username': 'zhang.zhuan',
            'email': 'zhang.zhuan@mytravel.com',
            'password': 'zhangzhuan123'
        },
        {
            'username': 'zhangzhuan',
            'email': 'zhangzhuan@mytravel.com',
            'password': 'zhangzhuan123'
        },
        {
            'username': 'zhang_zhuang',
            'email': 'zhang_zhuang@mytravel.com',
            'password': 'zhangzhuan123'
        }
    ]
    
    for i, alt in enumerate(alternatives, 1):
        print(f"\n备选方案 {i}:")
        print(f"   用户名: {alt['username']}")
        print(f"   邮箱: {alt['email']}")
        print(f"   密码: {alt['password']}")

def main():
    """主函数"""
    print("开始创建员工账户...")
    
    # 创建主账户
    success = create_employee_account()
    
    if success:
        # 生成备用账号信息
        generate_alternative_accounts()
        
        print("\n" + "=" * 50)
        print("🎉 账户创建完成！")
        print("=" * 50)
    else:
        print("\n❌ 账户创建失败")

if __name__ == "__main__":
    main() 
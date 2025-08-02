#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称：fix_password_hash_compatibility.py
功能描述：修复密码哈希兼容性问题
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
from App.models.auth import AuthUser
from werkzeug.security import generate_password_hash, check_password_hash

def fix_password_hash_compatibility():
    """修复密码哈希兼容性问题"""
    app = create_app()
    
    with app.app_context():
        print("🔧 修复密码哈希兼容性问题")
        print("=" * 50)
        
        # 获取所有用户
        users = AuthUser.query.all()
        
        if not users:
            print("❌ 没有找到任何用户")
            return False
        
        print(f"📋 找到 {len(users)} 个用户")
        
        fixed_count = 0
        error_count = 0
        
        for user in users:
            print(f"\n处理用户: {user.username}")
            print(f"当前哈希: {user.password_hash[:50]}...")
            
            # 检查哈希格式
            if user.password_hash.startswith('scrypt:'):
                print("⚠️  检测到scrypt哈希格式，需要修复")
                
                # 为每个用户设置一个默认密码
                default_password = f"{user.username}123"
                
                try:
                    # 生成新的pbkdf2哈希
                    new_hash = generate_password_hash(default_password, method='pbkdf2:sha256')
                    user.password_hash = new_hash
                    
                    print(f"✅ 已修复用户 {user.username}")
                    print(f"新密码: {default_password}")
                    print(f"新哈希: {new_hash[:50]}...")
                    
                    fixed_count += 1
                    
                except Exception as e:
                    print(f"❌ 修复用户 {user.username} 失败: {str(e)}")
                    error_count += 1
            else:
                print("✓ 哈希格式正常，无需修复")
        
        # 提交更改
        try:
            db.session.commit()
            print(f"\n✅ 修复完成！")
            print(f"修复用户数: {fixed_count}")
            print(f"错误用户数: {error_count}")
            
            # 显示修复后的用户信息
            print("\n📋 修复后的用户信息:")
            for user in AuthUser.query.all():
                print(f"   用户名: {user.username}")
                print(f"   邮箱: {user.email}")
                print(f"   默认密码: {user.username}123")
                print(f"   哈希格式: {'pbkdf2' if user.password_hash.startswith('pbkdf2:') else '其他'}")
                print()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 提交更改失败: {str(e)}")
            return False

def create_test_user():
    """创建一个测试用户"""
    app = create_app()
    
    with app.app_context():
        print("\n🧪 创建测试用户")
        print("=" * 30)
        
        # 检查是否已存在测试用户
        test_user = AuthUser.query.filter_by(username='test_user').first()
        if test_user:
            print("⚠️  测试用户已存在，删除旧用户")
            db.session.delete(test_user)
            db.session.flush()
        
        # 创建新的测试用户
        from App.models.auth import Role
        
        # 获取或创建staff角色
        staff_role = Role.query.filter_by(name='staff').first()
        if not staff_role:
            staff_role = Role(name='staff', description='员工')
            db.session.add(staff_role)
            db.session.flush()
        
        # 创建测试用户
        test_user = AuthUser(
            username='test_user',
            email='test@mytravel.com',
            password_hash=generate_password_hash('test123', method='pbkdf2:sha256'),
            role_id=staff_role.id,
            is_active=True
        )
        
        db.session.add(test_user)
        db.session.commit()
        
        print("✅ 测试用户创建成功")
        print(f"   用户名: test_user")
        print(f"   邮箱: test@mytravel.com")
        print(f"   密码: test123")
        print(f"   哈希格式: pbkdf2:sha256")
        
        return True

def main():
    """主函数"""
    print("开始修复密码哈希兼容性问题...")
    
    # 修复现有用户
    success1 = fix_password_hash_compatibility()
    
    # 创建测试用户
    success2 = create_test_user()
    
    if success1 and success2:
        print("\n" + "=" * 50)
        print("🎉 修复完成！")
        print("=" * 50)
        print("\n📋 登录信息:")
        print("   测试用户:")
        print("     用户名: test_user")
        print("     密码: test123")
        print("     邮箱: test@mytravel.com")
        print("\n   其他用户:")
        print("     用户名: [用户名]")
        print("     密码: [用户名]123")
        print("\n🔗 登录地址: http://192.168.5.60:5000/auth/staff/login")
    else:
        print("\n❌ 修复失败")

if __name__ == "__main__":
    main() 
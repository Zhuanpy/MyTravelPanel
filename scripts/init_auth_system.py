#!/usr/bin/env python3
"""
认证系统初始化脚本
用于创建认证相关的数据库表和初始化基础数据
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from App import create_app
from App.exts import db
from App.models.auth import Role, AuthUser, UserProfile, init_roles, create_default_admin

def init_auth_system():
    """初始化认证系统"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 开始初始化认证系统...")
            
            # 1. 创建所有表
            print("📋 创建数据库表...")
            db.create_all()
            print("✅ 数据库表创建完成")
            
            # 2. 初始化角色数据
            print("👥 初始化角色数据...")
            init_roles()
            print("✅ 角色数据初始化完成")
            
            # 3. 创建默认管理员
            print("👨‍💼 创建默认管理员账户...")
            create_default_admin()
            print("✅ 默认管理员创建完成")
            
            # 4. 验证初始化结果
            print("🔍 验证初始化结果...")
            roles = Role.query.all()
            print(f"✅ 角色数量: {len(roles)}")
            for role in roles:
                print(f"   - {role.name}: {role.description}")
            
            admin_user = AuthUser.query.filter_by(username='admin').first()
            if admin_user:
                print(f"✅ 默认管理员: {admin_user.username} ({admin_user.email})")
                print(f"   密码: admin123")
            else:
                print("❌ 默认管理员创建失败")
            
            print("\n🎉 认证系统初始化完成！")
            print("\n📝 默认登录信息:")
            print("   用户名: admin")
            print("   密码: admin123")
            print("   邮箱: admin@mytravelpanel.com")
            
        except Exception as e:
            print(f"❌ 初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

def check_auth_tables():
    """检查认证表是否存在"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查roles表
            roles_count = Role.query.count()
            print(f"✅ roles表存在，当前角色数量: {roles_count}")
            
            # 检查auth_users表
            from sqlalchemy import text
            result = db.session.execute(text("SHOW TABLES LIKE 'auth_users'"))
            if result.fetchone():
                users_count = AuthUser.query.count()
                print(f"✅ auth_users表存在，当前用户数量: {users_count}")
            else:
                print("❌ auth_users表不存在")
            
            # 检查user_profiles表
            result = db.session.execute(text("SHOW TABLES LIKE 'user_profiles'"))
            if result.fetchone():
                profiles_count = UserProfile.query.count()
                print(f"✅ user_profiles表存在，当前资料数量: {profiles_count}")
            else:
                print("❌ user_profiles表不存在")
                
        except Exception as e:
            print(f"❌ 检查失败: {str(e)}")
            return False
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='认证系统初始化工具')
    parser.add_argument('--check', action='store_true', help='检查认证表状态')
    parser.add_argument('--init', action='store_true', help='初始化认证系统')
    
    args = parser.parse_args()
    
    if args.check:
        print("🔍 检查认证表状态...")
        check_auth_tables()
    elif args.init:
        print("🚀 初始化认证系统...")
        init_auth_system()
    else:
        print("请选择操作:")
        print("  python scripts/init_auth_system.py --check  # 检查表状态")
        print("  python scripts/init_auth_system.py --init   # 初始化系统") 
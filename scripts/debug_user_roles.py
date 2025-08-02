#!/usr/bin/env python3
"""
调试用户角色问题
检查用户角色分配和登录跳转逻辑
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from App import create_app
from App.exts import db
from App.models.auth import Role, AuthUser, UserProfile

def debug_user_roles():
    """调试用户角色问题"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 调试用户角色问题...")
            
            # 1. 检查所有角色
            print("\n📋 角色列表:")
            roles = Role.query.all()
            for role in roles:
                print(f"   - ID: {role.id}, 名称: {role.name}, 描述: {role.description}")
            
            # 2. 检查所有用户
            print("\n👥 用户列表:")
            users = AuthUser.query.all()
            for user in users:
                role_name = user.role.name if user.role else "无角色"
                print(f"   - ID: {user.id}, 用户名: {user.username}, 邮箱: {user.email}, 角色: {role_name}")
            
            # 3. 测试登录逻辑
            print("\n🔐 测试登录跳转逻辑:")
            for user in users:
                role_name = user.role.name if user.role else "无角色"
                print(f"\n用户: {user.username} ({user.email})")
                print(f"角色: {role_name}")
                
                # 模拟登录后的跳转逻辑
                if role_name == 'admin':
                    print("   应该跳转到: admin.dashboard")
                elif role_name == 'staff':
                    print("   应该跳转到: staff.dashboard")
                elif role_name == 'member':
                    print("   应该跳转到: member.dashboard")
                else:
                    print("   应该跳转到: public.index (未知角色)")
            
            # 4. 检查特定用户
            print("\n🎯 检查特定用户:")
            test_email = "admin@mytravelpanel.com"  # 默认管理员邮箱
            user = AuthUser.query.filter_by(email=test_email).first()
            if user:
                print(f"找到用户: {user.username}")
                print(f"邮箱: {user.email}")
                print(f"角色: {user.role.name if user.role else '无角色'}")
                print(f"角色ID: {user.role_id}")
                if user.role:
                    print(f"角色描述: {user.role.description}")
                    print(f"角色权限: {user.role.permissions}")
            else:
                print(f"未找到邮箱为 {test_email} 的用户")
            
            # 5. 检查数据库表结构
            print("\n🗄️ 检查数据库表结构:")
            from sqlalchemy import text
            
            # 检查roles表
            result = db.session.execute(text("DESCRIBE roles"))
            print("roles表结构:")
            for row in result:
                print(f"   - {row[0]}: {row[1]}")
            
            # 检查auth_users表
            result = db.session.execute(text("DESCRIBE auth_users"))
            print("\nauth_users表结构:")
            for row in result:
                print(f"   - {row[0]}: {row[1]}")
            
            # 6. 检查外键关系
            print("\n🔗 检查外键关系:")
            result = db.session.execute(text("""
                SELECT 
                    u.id as user_id,
                    u.username,
                    u.email,
                    u.role_id,
                    r.id as role_id_check,
                    r.name as role_name
                FROM auth_users u
                LEFT JOIN roles r ON u.role_id = r.id
                ORDER BY u.id
            """))
            
            print("用户-角色关系:")
            for row in result:
                print(f"   - 用户ID: {row[0]}, 用户名: {row[1]}, 邮箱: {row[2]}")
                print(f"     角色ID: {row[3]}, 实际角色ID: {row[4]}, 角色名: {row[5]}")
            
        except Exception as e:
            print(f"❌ 调试失败: {str(e)}")
            import traceback
            traceback.print_exc()

def fix_user_roles():
    """修复用户角色问题"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 修复用户角色问题...")
            
            # 1. 确保所有用户都有正确的角色
            users = AuthUser.query.all()
            member_role = Role.query.filter_by(name='member').first()
            admin_role = Role.query.filter_by(name='admin').first()
            
            if not member_role:
                print("❌ member角色不存在，请先运行初始化脚本")
                return False
            
            if not admin_role:
                print("❌ admin角色不存在，请先运行初始化脚本")
                return False
            
            print(f"✅ 找到member角色: ID={member_role.id}")
            print(f"✅ 找到admin角色: ID={admin_role.id}")
            
            # 2. 修复用户角色
            fixed_count = 0
            for user in users:
                if not user.role_id:
                    # 如果用户没有角色，默认设置为member
                    user.role_id = member_role.id
                    fixed_count += 1
                    print(f"✅ 修复用户 {user.username} 的角色为 member")
                elif user.role_id == admin_role.id:
                    print(f"ℹ️  用户 {user.username} 已经是管理员")
                elif user.role_id == member_role.id:
                    print(f"ℹ️  用户 {user.username} 已经是会员")
                else:
                    # 如果角色ID无效，设置为member
                    user.role_id = member_role.id
                    fixed_count += 1
                    print(f"✅ 修复用户 {user.username} 的角色为 member")
            
            if fixed_count > 0:
                db.session.commit()
                print(f"✅ 修复了 {fixed_count} 个用户的角色")
            else:
                print("ℹ️  所有用户的角色都是正确的")
            
            return True
            
        except Exception as e:
            print(f"❌ 修复失败: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='调试用户角色问题')
    parser.add_argument('--debug', action='store_true', help='调试用户角色')
    parser.add_argument('--fix', action='store_true', help='修复用户角色问题')
    
    args = parser.parse_args()
    
    if args.debug:
        debug_user_roles()
    elif args.fix:
        fix_user_roles()
    else:
        print("请选择操作:")
        print("  python scripts/debug_user_roles.py --debug  # 调试用户角色")
        print("  python scripts/debug_user_roles.py --fix    # 修复用户角色问题") 
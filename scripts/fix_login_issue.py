#!/usr/bin/env python3
"""
修复登录问题脚本
解决三个登录入口都跳转到会员页面的问题
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

def fix_login_issue():
    """修复登录问题"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 修复登录问题...")
            
            # 1. 检查并创建角色
            print("📋 检查角色数据...")
            roles_data = [
                {
                    'name': 'admin',
                    'description': '系统管理员，拥有所有权限',
                    'permissions': [
                        'manage_all_data', 'manage_users', 'manage_roles', 
                        'manage_orders', 'publish_content', 'view_analytics', 'system_config'
                    ]
                },
                {
                    'name': 'staff',
                    'description': '公司员工，管理所属项目',
                    'permissions': [
                        'manage_own_projects', 'create_quotes', 'edit_quotes',
                        'upload_files', 'update_progress', 'view_own_orders'
                    ]
                },
                {
                    'name': 'member',
                    'description': '会员客户，可以下单查看订单',
                    'permissions': [
                        'view_own_orders', 'place_orders', 'view_quotes',
                        'view_invoices', 'edit_profile'
                    ]
                },
                {
                    'name': 'guest',
                    'description': '普通访客，只能浏览公开信息',
                    'permissions': [
                        'view_public_info', 'view_visa_services', 'view_tour_packages'
                    ]
                }
            ]
            
            # 创建角色
            for role_data in roles_data:
                role = Role.query.filter_by(name=role_data['name']).first()
                if not role:
                    role = Role(**role_data)
                    db.session.add(role)
                    print(f"✅ 创建角色: {role_data['name']}")
                else:
                    print(f"ℹ️  角色已存在: {role_data['name']}")
            
            db.session.commit()
            
            # 2. 创建测试用户
            print("\n👥 创建测试用户...")
            
            # 获取角色
            admin_role = Role.query.filter_by(name='admin').first()
            staff_role = Role.query.filter_by(name='staff').first()
            member_role = Role.query.filter_by(name='member').first()
            
            # 创建管理员用户
            admin_user = AuthUser.query.filter_by(email='admin@mytravelpanel.com').first()
            if not admin_user:
                admin_user = AuthUser(
                    username='admin',
                    email='admin@mytravelpanel.com',
                    role_id=admin_role.id,
                    is_active=True,
                    is_verified=True
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                print("✅ 创建管理员用户: admin@mytravelpanel.com")
                
                # 创建管理员资料
                admin_profile = UserProfile(
                    user_id=admin_user.id,
                    first_name='系统',
                    last_name='管理员',
                    company='MyTravelPanel',
                    position='系统管理员'
                )
                db.session.add(admin_profile)
            else:
                print("ℹ️  管理员用户已存在")
            
            # 创建员工用户
            staff_user = AuthUser.query.filter_by(email='staff@mytravelpanel.com').first()
            if not staff_user:
                staff_user = AuthUser(
                    username='staff',
                    email='staff@mytravelpanel.com',
                    role_id=staff_role.id,
                    is_active=True,
                    is_verified=True
                )
                staff_user.set_password('staff123')
                db.session.add(staff_user)
                print("✅ 创建员工用户: staff@mytravelpanel.com")
                
                # 创建员工资料
                staff_profile = UserProfile(
                    user_id=staff_user.id,
                    first_name='员工',
                    last_name='测试',
                    company='MyTravelPanel',
                    position='员工'
                )
                db.session.add(staff_profile)
            else:
                print("ℹ️  员工用户已存在")
            
            # 创建会员用户
            member_user = AuthUser.query.filter_by(email='member@mytravelpanel.com').first()
            if not member_user:
                member_user = AuthUser(
                    username='member',
                    email='member@mytravelpanel.com',
                    role_id=member_role.id,
                    is_active=True,
                    is_verified=True
                )
                member_user.set_password('member123')
                db.session.add(member_user)
                print("✅ 创建会员用户: member@mytravelpanel.com")
                
                # 创建会员资料
                member_profile = UserProfile(
                    user_id=member_user.id,
                    first_name='会员',
                    last_name='测试',
                    company='测试公司',
                    position='客户'
                )
                db.session.add(member_profile)
            else:
                print("ℹ️  会员用户已存在")
            
            db.session.commit()
            
            # 3. 验证用户角色
            print("\n🔍 验证用户角色...")
            users = AuthUser.query.all()
            for user in users:
                role_name = user.role.name if user.role else "无角色"
                print(f"   - {user.username} ({user.email}): {role_name}")
            
            print("\n🎉 修复完成！")
            print("\n📝 测试账户信息:")
            print("   管理员: admin@mytravelpanel.com / admin123")
            print("   员工: staff@mytravelpanel.com / staff123")
            print("   会员: member@mytravelpanel.com / member123")
            
            return True
            
        except Exception as e:
            print(f"❌ 修复失败: {str(e)}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

def test_login_redirects():
    """测试登录跳转逻辑"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 测试登录跳转逻辑...")
            
            users = AuthUser.query.all()
            for user in users:
                role_name = user.role.name if user.role else "无角色"
                print(f"\n用户: {user.username} ({user.email})")
                print(f"角色: {role_name}")
                
                # 模拟登录后的跳转逻辑
                if role_name == 'admin':
                    print("   应该跳转到: /admin/dashboard")
                elif role_name == 'staff':
                    print("   应该跳转到: /staff/dashboard")
                elif role_name == 'member':
                    print("   应该跳转到: /member/dashboard")
                else:
                    print("   应该跳转到: /public/index (未知角色)")
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='修复登录问题')
    parser.add_argument('--fix', action='store_true', help='修复登录问题')
    parser.add_argument('--test', action='store_true', help='测试登录跳转')
    
    args = parser.parse_args()
    
    if args.fix:
        fix_login_issue()
    elif args.test:
        test_login_redirects()
    else:
        print("请选择操作:")
        print("  python scripts/fix_login_issue.py --fix   # 修复登录问题")
        print("  python scripts/fix_login_issue.py --test  # 测试登录跳转") 
#!/usr/bin/env python3
"""
认证系统测试脚本
用于测试认证相关的功能
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

def test_roles():
    """测试角色系统"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 测试角色系统...")
            
            # 检查roles表是否存在
            from sqlalchemy import text
            result = db.session.execute(text("SHOW TABLES LIKE 'roles'"))
            if not result.fetchone():
                print("❌ roles表不存在")
                return False
            
            # 检查角色数据
            roles = Role.query.all()
            print(f"✅ 找到 {len(roles)} 个角色:")
            
            for role in roles:
                print(f"   - {role.name}: {role.description}")
                if role.permissions:
                    print(f"     权限数量: {len(role.permissions)}")
            
            # 检查member角色是否存在
            member_role = Role.query.filter_by(name='member').first()
            if member_role:
                print("✅ member角色存在")
                return True
            else:
                print("❌ member角色不存在")
                return False
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def test_user_registration():
    """测试用户注册功能"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔍 测试用户注册功能...")
            
            # 检查member角色
            member_role = Role.query.filter_by(name='member').first()
            if not member_role:
                print("❌ member角色不存在，无法测试注册")
                return False
            
            print(f"✅ member角色ID: {member_role.id}")
            
            # 模拟注册过程
            from werkzeug.security import generate_password_hash
            
            # 创建测试用户
            test_user = AuthUser(
                username='test_member',
                email='test@example.com',
                role_id=member_role.id,
                is_active=True,
                is_verified=True
            )
            test_user.set_password('test123')
            
            # 添加到数据库
            db.session.add(test_user)
            db.session.commit()
            
            print("✅ 测试用户创建成功")
            
            # 清理测试数据
            db.session.delete(test_user)
            db.session.commit()
            print("✅ 测试数据清理完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            db.session.rollback()
            return False

def fix_missing_roles():
    """修复缺失的角色数据"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 修复缺失的角色数据...")
            
            # 检查并创建角色
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
            
            created_count = 0
            for role_data in roles_data:
                role = Role.query.filter_by(name=role_data['name']).first()
                if not role:
                    role = Role(**role_data)
                    db.session.add(role)
                    created_count += 1
                    print(f"✅ 创建角色: {role_data['name']}")
                else:
                    print(f"ℹ️  角色已存在: {role_data['name']}")
            
            db.session.commit()
            print(f"✅ 修复完成，创建了 {created_count} 个新角色")
            
            return True
            
        except Exception as e:
            print(f"❌ 修复失败: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='认证系统测试工具')
    parser.add_argument('--test', action='store_true', help='测试角色系统')
    parser.add_argument('--test-registration', action='store_true', help='测试用户注册')
    parser.add_argument('--fix', action='store_true', help='修复缺失的角色数据')
    
    args = parser.parse_args()
    
    if args.test:
        test_roles()
    elif args.test_registration:
        test_user_registration()
    elif args.fix:
        fix_missing_roles()
    else:
        print("请选择操作:")
        print("  python scripts/test_auth_system.py --test              # 测试角色系统")
        print("  python scripts/test_auth_system.py --test-registration # 测试用户注册")
        print("  python scripts/test_auth_system.py --fix               # 修复缺失的角色数据") 
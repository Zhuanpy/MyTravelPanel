#!/usr/bin/env python3
"""
创建邀请码表的数据库迁移脚本
运行此脚本来创建 invitation_codes 表
"""

from App import create_app
from App.exts import db
from App.models.auth import InvitationCode

def create_invitation_codes_table():
    """创建邀请码表"""
    app = create_app()
    
    with app.app_context():
        # 创建表
        db.create_all()
        print("✅ 邀请码表创建成功！")
        
        # 创建一些示例邀请码（可选）
        create_sample_codes = input("是否创建示例邀请码？(y/n): ").lower().strip()
        
        if create_sample_codes == 'y':
            # 检查是否已有管理员用户
            from App.models.auth import AuthUser, Role
            admin_role = Role.query.filter_by(name='admin').first()
            admin_user = AuthUser.query.filter_by(role_id=admin_role.id).first() if admin_role else None
            
            if not admin_user:
                print("⚠️  未找到管理员用户，无法创建示例邀请码")
                return
            
            # 创建示例邀请码
            sample_codes = [
                {
                    'code': 'STAFF2025DEMO',
                    'role_name': 'staff',
                    'created_by': admin_user.id
                },
                {
                    'code': 'ADMIN2025DEMO', 
                    'role_name': 'admin',
                    'created_by': admin_user.id
                }
            ]
            
            for code_data in sample_codes:
                existing = InvitationCode.query.filter_by(code=code_data['code']).first()
                if not existing:
                    invitation_code = InvitationCode(**code_data)
                    db.session.add(invitation_code)
            
            db.session.commit()
            print("✅ 示例邀请码创建成功！")
            print("📋 示例邀请码:")
            print("   员工邀请码: STAFF2025DEMO")
            print("   管理员邀请码: ADMIN2025DEMO")

if __name__ == '__main__':
    create_invitation_codes_table() 
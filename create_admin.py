#!/usr/bin/env python3
"""
创建第一个超级管理员账户脚本
用于系统初始化时创建第一个管理员用户
"""

from App import create_app
from App.exts import db
from App.models.auth import AuthUser, Role, UserProfile
import getpass
import re

def create_first_admin():
    """创建第一个超级管理员"""
    app = create_app()
    
    with app.app_context():
        print("🚀 MyTravelPanel 系统初始化")
        print("=" * 50)
        
        # 检查是否已存在管理员
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            existing_admin = AuthUser.query.filter_by(role_id=admin_role.id).first()
            if existing_admin:
                print("⚠️  系统中已存在管理员账户:")
                print(f"   用户名: {existing_admin.username}")
                print(f"   邮箱: {existing_admin.email}")
                
                override = input("\n是否要创建新的管理员账户？(y/n): ").lower().strip()
                if override != 'y':
                    print("❌ 操作已取消")
                    return
        
        print("\n📝 请输入第一个超级管理员的信息:")
        print("-" * 30)
        
        # 获取管理员信息
        while True:
            email = input("邮箱地址: ").strip()
            if not email:
                print("❌ 邮箱不能为空")
                continue
            
            # 邮箱格式验证
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                print("❌ 邮箱格式不正确")
                continue
            
            # 检查邮箱是否已存在
            existing_user = AuthUser.query.filter_by(email=email).first()
            if existing_user:
                print("❌ 该邮箱已被注册")
                continue
            
            break
        
        while True:
            username = input("用户名: ").strip()
            if not username:
                print("❌ 用户名不能为空")
                continue
            
            if len(username) < 3:
                print("❌ 用户名至少3个字符")
                continue
            
            # 检查用户名是否已存在
            existing_user = AuthUser.query.filter_by(username=username).first()
            if existing_user:
                print("❌ 该用户名已被使用")
                continue
            
            break
        
        first_name = input("姓氏: ").strip()
        last_name = input("名字: ").strip()
        phone = input("联系电话 (可选): ").strip()
        
        while True:
            password = getpass.getpass("密码 (至少6位): ")
            if len(password) < 6:
                print("❌ 密码长度至少6位")
                continue
            
            confirm_password = getpass.getpass("确认密码: ")
            if password != confirm_password:
                print("❌ 两次输入的密码不一致")
                continue
            
            break
        
        print("\n🔄 创建管理员账户中...")
        
        try:
            # 确保管理员角色存在
            if not admin_role:
                admin_role = Role(name='admin', description='系统管理员')
                db.session.add(admin_role)
                db.session.commit()
            
            # 创建管理员用户
            admin_user = AuthUser(
                username=username,
                email=email,
                role_id=admin_role.id
            )
            admin_user.set_password(password)
            
            db.session.add(admin_user)
            db.session.commit()
            
            # 创建用户资料
            user_profile = UserProfile(
                user_id=admin_user.id,
                first_name=first_name,
                last_name=last_name,
                phone=phone
            )
            db.session.add(user_profile)
            db.session.commit()
            
            print("\n✅ 超级管理员创建成功！")
            print("=" * 30)
            print(f"🆔 用户名: {username}")
            print(f"📧 邮箱: {email}")
            print(f"👤 角色: 超级管理员")
            print("\n🎉 现在您可以使用以下方式登录:")
            print(f"   1. 访问: http://127.0.0.1:5000/portal")
            print(f"   2. 点击 '管理员后台' 卡片")
            print(f"   3. 使用上述邮箱和密码登录")
            print(f"   4. 登录后可以在管理员后台创建邀请码")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ 创建管理员失败: {str(e)}")

def check_system_status():
    """检查系统状态"""
    app = create_app()
    
    with app.app_context():
        print("📊 系统状态检查")
        print("=" * 30)
        
        # 检查角色
        roles = Role.query.all()
        print(f"系统角色数: {len(roles)}")
        for role in roles:
            user_count = AuthUser.query.filter_by(role_id=role.id).count()
            print(f"  - {role.name}: {user_count} 用户")
        
        # 检查管理员
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            admin_count = AuthUser.query.filter_by(role_id=admin_role.id).count()
            if admin_count > 0:
                print(f"\n✅ 系统中有 {admin_count} 个管理员账户")
                admins = AuthUser.query.filter_by(role_id=admin_role.id).all()
                for admin in admins:
                    print(f"  - {admin.username} ({admin.email})")
            else:
                print("\n⚠️  系统中没有管理员账户")
        else:
            print("\n❌ 管理员角色不存在")

if __name__ == '__main__':
    print("MyTravelPanel 系统管理工具")
    print("1. 创建超级管理员")
    print("2. 检查系统状态")
    
    choice = input("\n请选择操作 (1/2): ").strip()
    
    if choice == '1':
        create_first_admin()
    elif choice == '2':
        check_system_status()
    else:
        print("❌ 无效的选择") 
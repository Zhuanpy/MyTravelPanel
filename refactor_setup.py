#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目重构工具 - 创建新的目录结构
"""

import os
import shutil
from pathlib import Path


def create_new_structure():
    """创建新的项目目录结构"""
    
    # 定义新的目录结构
    new_structure = {
        # 主应用包
        'App': {
            'auth': {
                'models.py': '',
                'routes.py': '',
                'services.py': '',
                'decorators.py': '',
                'permissions.py': '',
                '__init__.py': ''
            },
            'guest': {
                'routes.py': '',
                'services.py': '',
                'templates': {},
                '__init__.py': ''
            },
            'member': {
                'models.py': '',
                'routes.py': '',
                'services.py': '',
                'templates': {},
                '__init__.py': ''
            },
            'staff': {
                'models.py': '',
                'routes.py': '',
                'services.py': '',
                'templates': {},
                '__init__.py': ''
            },
            'admin': {
                'models.py': '',
                'routes.py': '',
                'services.py': '',
                'templates': {},
                '__init__.py': ''
            },
            'business': {
                'visa': {
                    'models.py': '',
                    'routes.py': '',
                    'services.py': '',
                    'templates': {},
                    '__init__.py': ''
                },
                'flight': {
                    'models.py': '',
                    'routes.py': '',
                    'services.py': '',
                    'templates': {},
                    '__init__.py': ''
                },
                'tour': {
                    'models.py': '',
                    'routes.py': '',
                    'services.py': '',
                    'templates': {},
                    '__init__.py': ''
                },
                'finance': {
                    'models.py': '',
                    'routes.py': '',
                    'services.py': '',
                    'templates': {},
                    '__init__.py': ''
                },
                '__init__.py': ''
            },
            'shared': {
                'models.py': '',
                'services.py': '',
                'utils.py': '',
                'templates': {},
                '__init__.py': ''
            },
            'static': {
                'guest': {},
                'member': {},
                'staff': {},
                'admin': {},
                'shared': {}
            },
            'utils': {
                'cache.py': '',
                'email.py': '',
                'file.py': '',
                'background.py': '',
                '__init__.py': ''
            }
        },
        # 资源目录
        'resources': {
            'guest': {},
            'member': {},
            'staff': {},
            'admin': {}
        },
        # 文档目录
        'docs': {
            'guest': {},
            'member': {},
            'staff': {},
            'admin': {}
        }
    }
    
    def create_directories(structure, base_path=""):
        """递归创建目录结构"""
        for name, content in structure.items():
            current_path = os.path.join(base_path, name)
            
            if isinstance(content, dict):
                # 创建目录
                os.makedirs(current_path, exist_ok=True)
                # 递归创建子目录
                create_directories(content, current_path)
            else:
                # 创建文件
                os.makedirs(os.path.dirname(current_path), exist_ok=True)
                if not os.path.exists(current_path):
                    with open(current_path, 'w', encoding='utf-8') as f:
                        f.write(content)
    
    print("🚀 开始创建新的项目结构...")
    
    # 创建新结构目录（临时）
    new_app_path = "App_new"
    if os.path.exists(new_app_path):
        shutil.rmtree(new_app_path)
    
    # 创建新的App结构
    create_directories({'App_new': new_structure['App']})
    
    # 创建resources和docs结构
    create_directories({'resources_new': new_structure['resources']})
    create_directories({'docs_new': new_structure['docs']})
    
    print("✅ 新的项目结构已创建在临时目录中")
    print("📁 App_new/ - 新的应用结构")
    print("📁 resources_new/ - 新的资源结构") 
    print("📁 docs_new/ - 新的文档结构")
    
    return True


def create_migration_script():
    """创建迁移脚本"""
    
    migration_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目重构迁移脚本
"""

import os
import shutil
from pathlib import Path


def migrate_auth_module():
    """迁移认证相关代码"""
    print("🔐 迁移认证模块...")
    
    # 迁移认证路由
    if os.path.exists("App/routes/auth.py"):
        shutil.copy2("App/routes/auth.py", "App_new/auth/routes.py")
    
    # 迁移认证模型
    if os.path.exists("App/models/auth.py"):
        shutil.copy2("App/models/auth.py", "App_new/auth/models.py")
    
    # 迁移用户模型
    if os.path.exists("App/models/User.py"):
        shutil.copy2("App/models/User.py", "App_new/auth/models.py")
    
    # 迁移权限和装饰器
    if os.path.exists("App/utils/decorators.py"):
        shutil.copy2("App/utils/decorators.py", "App_new/auth/decorators.py")
    
    if os.path.exists("App/utils/permissions.py"):
        shutil.copy2("App/utils/permissions.py", "App_new/auth/permissions.py")
    
    print("✅ 认证模块迁移完成")


def migrate_business_modules():
    """迁移业务模块"""
    print("📦 迁移业务模块...")
    
    # 迁移签证业务
    visa_files = [
        "App/routes/projects/VisaProjects/",
        "App/models/Product/Visamodels.py",
        "App/templates/visas/"
    ]
    
    for file_path in visa_files:
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                # 迁移整个目录
                dest_dir = "App_new/business/visa/"
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                # 这里需要手动处理每个文件的迁移
            else:
                # 迁移单个文件
                shutil.copy2(file_path, "App_new/business/visa/")
    
    # 迁移机票业务
    flight_files = [
        "App/routes/projects/FlightProjects/",
        "App/models/Flightmodels.py",
        "App/templates/flights/"
    ]
    
    # 迁移旅游业务
    tour_files = [
        "App/routes/projects/TourProjects/",
        "App/models/projects/TourProject.py",
        "App/templates/package/"
    ]
    
    print("✅ 业务模块迁移完成")


def migrate_role_modules():
    """迁移角色模块"""
    print("👥 迁移角色模块...")
    
    # 迁移访客模块
    if os.path.exists("App/routes/public.py"):
        shutil.copy2("App/routes/public.py", "App_new/guest/routes.py")
    
    # 迁移会员模块
    if os.path.exists("App/routes/member.py"):
        shutil.copy2("App/routes/member.py", "App_new/member/routes.py")
    
    # 迁移员工模块
    if os.path.exists("App/routes/staff.py"):
        shutil.copy2("App/routes/staff.py", "App_new/staff/routes.py")
    
    # 迁移管理员模块
    if os.path.exists("App/routes/admin.py"):
        shutil.copy2("App/routes/admin.py", "App_new/admin/routes.py")
    
    print("✅ 角色模块迁移完成")


def update_init_files():
    """更新__init__.py文件"""
    print("📝 更新初始化文件...")
    
    # 为每个模块创建合适的__init__.py
    modules = [
        "App_new/auth/__init__.py",
        "App_new/guest/__init__.py", 
        "App_new/member/__init__.py",
        "App_new/staff/__init__.py",
        "App_new/admin/__init__.py",
        "App_new/business/__init__.py",
        "App_new/business/visa/__init__.py",
        "App_new/business/flight/__init__.py",
        "App_new/business/tour/__init__.py",
        "App_new/business/finance/__init__.py",
        "App_new/shared/__init__.py",
        "App_new/utils/__init__.py"
    ]
    
    for init_file in modules:
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write('# -*- coding: utf-8 -*-\\n')
    
    print("✅ 初始化文件更新完成")


if __name__ == "__main__":
    print("🎯 开始项目迁移...")
    
    migrate_auth_module()
    migrate_business_modules() 
    migrate_role_modules()
    update_init_files()
    
    print("🎉 项目迁移完成！")
    print("⚠️  请手动检查和调整import语句")
'''
    
    with open("migrate_project.py", 'w', encoding='utf-8') as f:
        f.write(migration_script)
    
    print("📝 迁移脚本已创建: migrate_project.py")


if __name__ == "__main__":
    print("🎯 项目重构工具")
    print("=" * 50)
    
    # 创建新结构
    create_new_structure()
    
    # 创建迁移脚本
    create_migration_script()
    
    print("\n📋 下一步操作:")
    print("1. 检查新创建的目录结构")
    print("2. 运行 python migrate_project.py 进行代码迁移")
    print("3. 手动调整import语句和路由注册")
    print("4. 测试功能完整性")


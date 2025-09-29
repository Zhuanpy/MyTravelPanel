#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试路由注册问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("1. 导入项目EO模块...")
    from App_new.business.projects.routes.project_eo import project_eo
    print("   ✓ 项目EO模块导入成功")
    
    print("2. 检查蓝图名称...")
    print(f"   蓝图名称: {project_eo.name}")
    print(f"   URL前缀: {project_eo.url_prefix}")
    
    print("3. 检查路由规则...")
    for rule in project_eo.url_map.iter_rules():
        print(f"   路由: {rule}")
        print(f"   方法: {rule.methods}")
        print(f"   端点: {rule.endpoint}")
        print()
    
    print("4. 导入项目管理蓝图...")
    from App_new.business.projects import projects_bp
    print("   ✓ 项目管理蓝图导入成功")
    
    print("5. 检查项目管理蓝图的路由...")
    for rule in projects_bp.url_map.iter_rules():
        if 'eo' in str(rule):
            print(f"   EO路由: {rule}")
            print(f"   方法: {rule.methods}")
            print(f"   端点: {rule.endpoint}")
            print()
    
    print("6. 创建应用...")
    from App_new import create_app
    app = create_app()
    print("   ✓ 应用创建成功")
    
    print("7. 检查应用中的EO路由...")
    eo_routes = []
    for rule in app.url_map.iter_rules():
        if 'eo' in str(rule):
            eo_routes.append(rule)
    
    if eo_routes:
        print("   找到EO路由:")
        for rule in eo_routes:
            print(f"     {rule}")
            print(f"     方法: {rule.methods}")
            print(f"     端点: {rule.endpoint}")
            print()
    else:
        print("   ❌ 没有找到EO路由")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

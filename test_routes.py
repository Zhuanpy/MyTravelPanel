#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试路由注册
"""

try:
    from App_new import create_app
    app = create_app()
    
    print("=== 所有EO相关路由 ===")
    for rule in app.url_map.iter_rules():
        if 'eo' in str(rule):
            print(f"路由: {rule}")
            print(f"  方法: {rule.methods}")
            print(f"  端点: {rule.endpoint}")
            print()
    
    print("=== 所有项目相关路由 ===")
    for rule in app.url_map.iter_rules():
        if 'project' in str(rule):
            print(f"路由: {rule}")
            print(f"  方法: {rule.methods}")
            print(f"  端点: {rule.endpoint}")
            print()
            
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

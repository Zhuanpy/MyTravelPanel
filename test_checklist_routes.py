"""测试 checklist 路由是否正确注册"""

try:
    print("=" * 60)
    print("测试 Checklist 路由注册")
    print("=" * 60)
    print()
    
    # 导入应用
    print("1. 导入应用...")
    from app_new import app
    print("   ✅ 应用导入成功")
    print()
    
    # 检查蓝图
    print("2. 检查已注册的蓝图...")
    print(f"   注册的蓝图数量: {len(app.blueprints)}")
    if 'checklist' in app.blueprints:
        print("   ✅ checklist 蓝图已注册")
        bp = app.blueprints['checklist']
        print(f"   - 蓝图名称: {bp.name}")
        print(f"   - URL 前缀: {bp.url_prefix}")
    else:
        print("   ❌ checklist 蓝图未注册")
        print(f"   已注册的蓝图: {list(app.blueprints.keys())}")
    print()
    
    # 检查路由
    print("3. 检查 checklist 相关路由...")
    checklist_routes = []
    for rule in app.url_map.iter_rules():
        if 'checklist' in rule.rule or 'checklist' in rule.endpoint:
            checklist_routes.append({
                'rule': rule.rule,
                'endpoint': rule.endpoint,
                'methods': list(rule.methods)
            })
    
    if checklist_routes:
        print(f"   找到 {len(checklist_routes)} 个路由:")
        for route in checklist_routes:
            print(f"   ✅ {route['rule']}")
            print(f"      -> {route['endpoint']}")
            print(f"      -> 方法: {', '.join(route['methods'])}")
    else:
        print("   ❌ 未找到 checklist 相关路由")
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    
except Exception as e:
    print()
    print("=" * 60)
    print(f"❌ 错误: {e}")
    print("=" * 60)
    import traceback
    traceback.print_exc()












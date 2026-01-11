# -*- coding: utf-8 -*-
"""
测试供应商迁移后的代码是否正常工作
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """测试模型导入"""
    print('=' * 60)
    print('测试 1: 模型导入验证')
    print('=' * 60)

    results = []

    try:
        from App_new.business.projects.models.project import CustomerCompany
        print('[OK] CustomerCompany 导入成功')

        # 测试向后兼容属性
        print('  - 向后兼容属性检查:')
        c = CustomerCompany(
            company_name='Test Company',
            contact_phone='12345',
            contact_email='test@test.com',
            remarks='test notes'
        )
        print(f'    name: {c.name}')
        print(f'    phone: {c.phone}')
        print(f'    email: {c.email}')
        print(f'    notes: {c.notes}')
        results.append(('CustomerCompany', True, None))
    except Exception as e:
        print(f'[FAIL] CustomerCompany 导入失败: {e}')
        results.append(('CustomerCompany', False, str(e)))

    try:
        from App_new.shared.models.Suppliers import Supplier, get_suppliers, get_supplier_by_id
        print('[OK] Suppliers 兼容层导入成功')
        print(f'  - Supplier is CustomerCompany: {Supplier is CustomerCompany}')
        results.append(('Suppliers兼容层', True, None))
    except Exception as e:
        print(f'[FAIL] Suppliers 兼容层导入失败: {e}')
        results.append(('Suppliers兼容层', False, str(e)))

    try:
        from App_new.shared.models.account import Account
        print('[OK] Account 模型导入成功')
        results.append(('Account', True, None))
    except Exception as e:
        print(f'[FAIL] Account 模型导入失败: {e}')
        results.append(('Account', False, str(e)))

    try:
        from App_new.business.projects.models.supplier_prepayment import SupplierPrepayment
        print('[OK] SupplierPrepayment 模型导入成功')
        results.append(('SupplierPrepayment', True, None))
    except Exception as e:
        print(f'[FAIL] SupplierPrepayment 模型导败: {e}')
        results.append(('SupplierPrepayment', False, str(e)))

    try:
        from App_new.finance.models.statement import SupplierStatement
        print('[OK] SupplierStatement 模型导入成功')
        results.append(('SupplierStatement', True, None))
    except Exception as e:
        print(f'[FAIL] SupplierStatement 模型导入失败: {e}')
        results.append(('SupplierStatement', False, str(e)))

    return results


def test_blueprints():
    """测试路由蓝图导入"""
    print()
    print('=' * 60)
    print('测试 2: 路由蓝图导入验证')
    print('=' * 60)

    results = []

    blueprints = [
        ('App_new.shared.routes.supplier', 'supplier'),
        ('App_new.shared.routes.corporate', 'corporate'),
        ('App_new.shared.routes.account', 'account_routes'),
        ('App_new.business.projects.routes.project_prepayment', 'project_prepayment'),
        ('App_new.business.tour.routes.tour_products', 'tour_products_bp'),
        ('App_new.business.flight.routes.flights_booking_routes', 'flights_booking'),
        ('App_new.mobile.routes', 'mobile_bp'),
    ]

    for module_name, bp_name in blueprints:
        try:
            module = __import__(module_name, fromlist=[bp_name])
            bp = getattr(module, bp_name)
            print(f'[OK] {bp_name} 路由蓝图导入成功')
            results.append((bp_name, True, None))
        except Exception as e:
            print(f'[FAIL] {bp_name} 路由蓝图导入失败: {e}')
            results.append((bp_name, False, str(e)))

    return results


def test_app_factory():
    """测试应用工厂函数"""
    print()
    print('=' * 60)
    print('测试 3: Flask 应用创建')
    print('=' * 60)

    try:
        from App_new import create_app
        app = create_app()
        print('[OK] Flask 应用创建成功')
        print(f'  - 已注册蓝图数量: {len(app.blueprints)}')

        # 检查关键蓝图是否注册
        key_blueprints = ['supplier', 'corporate', 'account_routes', 'business_projects']
        for bp in key_blueprints:
            if bp in app.blueprints:
                print(f'  - {bp}: 已注册')
            else:
                print(f'  - {bp}: 未注册')

        return True, None
    except Exception as e:
        import traceback
        print(f'[FAIL] Flask 应用创建失败: {e}')
        traceback.print_exc()
        return False, str(e)


def test_database_queries():
    """测试数据库查询"""
    print()
    print('=' * 60)
    print('测试 4: 数据库查询验证')
    print('=' * 60)

    try:
        from App_new import create_app
        from App_new.exts import db
        from App_new.business.projects.models.project import CustomerCompany

        app = create_app()

        with app.app_context():
            # 测试供应商查询
            suppliers = CustomerCompany.query.filter(
                CustomerCompany.is_supplier == True,
                CustomerCompany.status == 'active'
            ).limit(5).all()

            print(f'[OK] 供应商查询成功，找到 {len(suppliers)} 条记录')

            for s in suppliers[:3]:
                print(f'  - ID: {s.id}, 名称: {s.name}, 类型: {s.supplier_type_display}')

            # 测试客户查询
            customers = CustomerCompany.query.filter(
                CustomerCompany.is_customer == True,
                CustomerCompany.status == 'active'
            ).limit(5).all()

            print(f'[OK] 客户查询成功，找到 {len(customers)} 条记录')

            # 统计
            total = CustomerCompany.query.count()
            supplier_count = CustomerCompany.query.filter(CustomerCompany.is_supplier == True).count()
            customer_count = CustomerCompany.query.filter(CustomerCompany.is_customer == True).count()
            both_count = CustomerCompany.query.filter(
                CustomerCompany.is_supplier == True,
                CustomerCompany.is_customer == True
            ).count()

            print()
            print('  公司统计:')
            print(f'    总数: {total}')
            print(f'    供应商: {supplier_count}')
            print(f'    客户: {customer_count}')
            print(f'    同时是客户和供应商: {both_count}')

        return True, None
    except Exception as e:
        import traceback
        print(f'[FAIL] 数据库查询失败: {e}')
        traceback.print_exc()
        return False, str(e)


if __name__ == '__main__':
    print()
    print('供应商迁移测试脚本')
    print('=' * 60)
    print()

    # 运行测试
    import_results = test_imports()
    bp_results = test_blueprints()
    app_result = test_app_factory()
    db_result = test_database_queries()

    # 汇总结果
    print()
    print('=' * 60)
    print('测试结果汇总')
    print('=' * 60)

    all_passed = True

    for name, passed, error in import_results + bp_results:
        status = '[OK]' if passed else '[FAIL]'
        print(f'{status} {name}')
        if not passed:
            all_passed = False

    print(f"{'[OK]' if app_result[0] else '[FAIL]'} Flask应用创建")
    print(f"{'[OK]' if db_result[0] else '[FAIL]'} 数据库查询")

    if not app_result[0]:
        all_passed = False
    if not db_result[0]:
        all_passed = False

    print()
    if all_passed:
        print('所有测试通过!')
    else:
        print('部分测试失败，请检查上述错误信息')

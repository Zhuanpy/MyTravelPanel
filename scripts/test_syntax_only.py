# -*- coding: utf-8 -*-
"""
简单的语法检查 - 检查代码是否可以正确解析
不需要完整的 Flask 环境
"""

import sys
import os
import ast

# 需要检查的文件列表
FILES_TO_CHECK = [
    'App_new/business/projects/models/project.py',
    'App_new/shared/models/Suppliers.py',
    'App_new/shared/models/account.py',
    'App_new/shared/models/__init__.py',
    'App_new/business/projects/models/supplier_prepayment.py',
    'App_new/finance/models/statement.py',
    'App_new/shared/routes/supplier.py',
    'App_new/shared/routes/account.py',
    'App_new/business/projects/routes/project_prepayment.py',
    'App_new/business/projects/routes/project_ref.py',
    'App_new/business/projects/routes/project_eo.py',
    'App_new/business/projects/forms/ref_forms.py',
    'App_new/business/tour/routes/tour_products.py',
    'App_new/business/flight/routes/flights_booking_routes.py',
    'App_new/mobile/routes.py',
    'App_new/business/finance/routes_supplier.py',
]

def check_syntax(filepath):
    """检查Python文件语法"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def check_imports_pattern(filepath):
    """检查文件中是否有正确的导入模式"""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否仍然有旧的 Supplier.query 模式（除了兼容层文件）
        if 'Suppliers.py' not in filepath and 'supplier.py' not in filepath:
            if 'Supplier.query' in content:
                # 检查上下文
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'Supplier.query' in line and '#' not in line.split('Supplier.query')[0]:
                        issues.append(f"Line {i+1}: 发现 Supplier.query 调用")

        # 检查是否有 suppliers.supplier_id 外键引用
        if 'suppliers.supplier_id' in content.lower():
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'suppliers.supplier_id' in line.lower():
                    issues.append(f"Line {i+1}: 发现 suppliers.supplier_id 外键引用")

    except Exception as e:
        issues.append(f"读取文件失败: {e}")

    return issues

def main():
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print('供应商迁移 - 代码检查')
    print('=' * 60)
    print()

    all_passed = True

    print('1. 语法检查')
    print('-' * 40)

    for file_rel in FILES_TO_CHECK:
        filepath = os.path.join(base_path, file_rel)
        if os.path.exists(filepath):
            passed, error = check_syntax(filepath)
            if passed:
                print(f'[OK] {file_rel}')
            else:
                print(f'[FAIL] {file_rel}')
                print(f'       {error}')
                all_passed = False
        else:
            print(f'[SKIP] {file_rel} (文件不存在)')

    print()
    print('2. 导入模式检查')
    print('-' * 40)

    for file_rel in FILES_TO_CHECK:
        filepath = os.path.join(base_path, file_rel)
        if os.path.exists(filepath):
            issues = check_imports_pattern(filepath)
            if not issues:
                print(f'[OK] {file_rel}')
            else:
                print(f'[WARN] {file_rel}')
                for issue in issues:
                    print(f'       {issue}')

    print()
    print('=' * 60)

    if all_passed:
        print('语法检查通过!')
    else:
        print('发现语法错误，请修复')

    # 检查 CustomerCompany 模型中的向后兼容属性
    print()
    print('3. CustomerCompany 向后兼容属性检查')
    print('-' * 40)

    project_model = os.path.join(base_path, 'App_new/business/projects/models/project.py')
    if os.path.exists(project_model):
        with open(project_model, 'r', encoding='utf-8') as f:
            content = f.read()

        required_properties = ['def name(self)', 'def phone(self)', 'def email(self)', 'def notes(self)']
        for prop in required_properties:
            if prop in content:
                print(f'[OK] {prop} 属性存在')
            else:
                print(f'[WARN] {prop} 属性缺失')

if __name__ == '__main__':
    main()

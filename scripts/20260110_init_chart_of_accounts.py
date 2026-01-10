# -*- coding: utf-8 -*-
"""
初始化会计科目表脚本
创建日期: 2026-01-10
说明: 根据旅行社业务需求初始化会计科目
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def init_chart_of_accounts():
    """初始化会计科目表"""
    from App_new.exts import db
    from App_new.finance.models.chart_of_account import ChartOfAccount

    print("=" * 60)
    print("初始化会计科目表 - 旅行社业务")
    print("=" * 60)

    # 定义会计科目结构
    accounts_data = [
        # ==================== 资产类 (1xxx) ====================
        {'code': '1000', 'name': 'Assets', 'name_cn': '资产',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 1, 'is_system': True},

        # 现金和银行
        {'code': '1001', 'name': 'Cash on Hand', 'name_cn': '库存现金',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 2, 'parent_code': '1000', 'is_system': True},
        {'code': '1002', 'name': 'Bank - SGD', 'name_cn': '银行存款-新币',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 2, 'parent_code': '1000', 'is_system': True},
        {'code': '1003', 'name': 'Bank - USD', 'name_cn': '银行存款-美元',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 2, 'parent_code': '1000', 'is_system': True},
        {'code': '1004', 'name': 'Bank - CNY', 'name_cn': '银行存款-人民币',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 2, 'parent_code': '1000', 'is_system': True},

        # 应收账款
        {'code': '1100', 'name': 'Accounts Receivable', 'name_cn': '应收账款',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 2, 'parent_code': '1000', 'is_system': True},
        {'code': '1101', 'name': 'AR - Corporate Clients', 'name_cn': '应收账款-公司客户',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 3, 'parent_code': '1100', 'is_system': False},
        {'code': '1102', 'name': 'AR - Individual Clients', 'name_cn': '应收账款-个人客户',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 3, 'parent_code': '1100', 'is_system': False},

        # 预付账款
        {'code': '1200', 'name': 'Prepayments', 'name_cn': '预付账款',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 2, 'parent_code': '1000', 'is_system': True},
        {'code': '1201', 'name': 'Prepaid - Airlines', 'name_cn': '预付-航空公司',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 3, 'parent_code': '1200', 'is_system': False},
        {'code': '1202', 'name': 'Prepaid - Hotels', 'name_cn': '预付-酒店',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 3, 'parent_code': '1200', 'is_system': False},
        {'code': '1203', 'name': 'Prepaid - Suppliers', 'name_cn': '预付-供应商',
         'account_type': 'asset', 'balance_direction': 'debit', 'level': 3, 'parent_code': '1200', 'is_system': False},

        # ==================== 负债类 (2xxx) ====================
        {'code': '2000', 'name': 'Liabilities', 'name_cn': '负债',
         'account_type': 'liability', 'balance_direction': 'credit', 'level': 1, 'is_system': True},

        # 应付账款
        {'code': '2100', 'name': 'Accounts Payable', 'name_cn': '应付账款',
         'account_type': 'liability', 'balance_direction': 'credit', 'level': 2, 'parent_code': '2000', 'is_system': True},
        {'code': '2101', 'name': 'AP - Airlines', 'name_cn': '应付-航空公司',
         'account_type': 'liability', 'balance_direction': 'credit', 'level': 3, 'parent_code': '2100', 'is_system': False},
        {'code': '2102', 'name': 'AP - Hotels', 'name_cn': '应付-酒店',
         'account_type': 'liability', 'balance_direction': 'credit', 'level': 3, 'parent_code': '2100', 'is_system': False},
        {'code': '2103', 'name': 'AP - Tour Operators', 'name_cn': '应付-地接社',
         'account_type': 'liability', 'balance_direction': 'credit', 'level': 3, 'parent_code': '2100', 'is_system': False},
        {'code': '2104', 'name': 'AP - Visa Agents', 'name_cn': '应付-签证代理',
         'account_type': 'liability', 'balance_direction': 'credit', 'level': 3, 'parent_code': '2100', 'is_system': False},
        {'code': '2105', 'name': 'AP - Transport', 'name_cn': '应付-用车服务',
         'account_type': 'liability', 'balance_direction': 'credit', 'level': 3, 'parent_code': '2100', 'is_system': False},

        # 预收账款
        {'code': '2200', 'name': 'Deposits Received', 'name_cn': '预收账款',
         'account_type': 'liability', 'balance_direction': 'credit', 'level': 2, 'parent_code': '2000', 'is_system': True},

        # 其他应付
        {'code': '2300', 'name': 'Other Payables', 'name_cn': '其他应付款',
         'account_type': 'liability', 'balance_direction': 'credit', 'level': 2, 'parent_code': '2000', 'is_system': True},

        # ==================== 权益类 (3xxx) ====================
        {'code': '3000', 'name': 'Equity', 'name_cn': '所有者权益',
         'account_type': 'equity', 'balance_direction': 'credit', 'level': 1, 'is_system': True},
        {'code': '3100', 'name': 'Share Capital', 'name_cn': '股本',
         'account_type': 'equity', 'balance_direction': 'credit', 'level': 2, 'parent_code': '3000', 'is_system': True},
        {'code': '3200', 'name': 'Retained Earnings', 'name_cn': '留存收益',
         'account_type': 'equity', 'balance_direction': 'credit', 'level': 2, 'parent_code': '3000', 'is_system': True},

        # ==================== 收入类 (4xxx) ====================
        {'code': '4000', 'name': 'Revenue', 'name_cn': '营业收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 1, 'is_system': True},

        # 销售收入
        {'code': '4100', 'name': 'Sales Revenue', 'name_cn': '销售收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 2, 'parent_code': '4000', 'is_system': True},
        {'code': '4101', 'name': 'Flight Ticket Sales', 'name_cn': '机票销售收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': False},
        {'code': '4102', 'name': 'Tour Package Sales', 'name_cn': '旅游产品销售收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': False},
        {'code': '4103', 'name': 'Visa Service Revenue', 'name_cn': '签证服务收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': False},
        {'code': '4104', 'name': 'Hotel Booking Revenue', 'name_cn': '酒店预订收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': False},
        {'code': '4105', 'name': 'Transport Service Revenue', 'name_cn': '用车服务收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': False},
        {'code': '4106', 'name': 'Insurance Revenue', 'name_cn': '保险销售收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': False},
        {'code': '4109', 'name': 'Other Service Revenue', 'name_cn': '其他服务收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 3, 'parent_code': '4100', 'is_system': False},

        # 佣金收入
        {'code': '4200', 'name': 'Commission Income', 'name_cn': '佣金收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 2, 'parent_code': '4000', 'is_system': True},

        # 其他收入
        {'code': '4900', 'name': 'Other Income', 'name_cn': '其他收入',
         'account_type': 'income', 'balance_direction': 'credit', 'level': 2, 'parent_code': '4000', 'is_system': True},

        # ==================== 成本费用类 (5xxx) ====================
        {'code': '5000', 'name': 'Cost of Sales', 'name_cn': '营业成本',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 1, 'is_system': True},

        # 销售成本
        {'code': '5100', 'name': 'Direct Costs', 'name_cn': '直接成本',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '5000', 'is_system': True},
        {'code': '5101', 'name': 'Flight Ticket Cost', 'name_cn': '机票成本',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': False},
        {'code': '5102', 'name': 'Tour Package Cost', 'name_cn': '旅游产品成本',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': False},
        {'code': '5103', 'name': 'Visa Service Cost', 'name_cn': '签证服务成本',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': False},
        {'code': '5104', 'name': 'Hotel Booking Cost', 'name_cn': '酒店预订成本',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': False},
        {'code': '5105', 'name': 'Transport Service Cost', 'name_cn': '用车服务成本',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': False},
        {'code': '5106', 'name': 'Insurance Cost', 'name_cn': '保险成本',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': False},
        {'code': '5109', 'name': 'Other Service Cost', 'name_cn': '其他服务成本',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 3, 'parent_code': '5100', 'is_system': False},

        # ==================== 运营费用类 (6xxx) ====================
        {'code': '6000', 'name': 'Operating Expenses', 'name_cn': '营业费用',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 1, 'is_system': True},

        {'code': '6100', 'name': 'Salary & Wages', 'name_cn': '工资薪金',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '6000', 'is_system': False},
        {'code': '6200', 'name': 'Rent Expense', 'name_cn': '租金费用',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '6000', 'is_system': False},
        {'code': '6300', 'name': 'Utilities', 'name_cn': '水电费',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '6000', 'is_system': False},
        {'code': '6400', 'name': 'Marketing & Advertising', 'name_cn': '市场推广费',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '6000', 'is_system': False},
        {'code': '6500', 'name': 'Office Supplies', 'name_cn': '办公用品',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '6000', 'is_system': False},
        {'code': '6600', 'name': 'Bank Charges', 'name_cn': '银行手续费',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '6000', 'is_system': False},
        {'code': '6700', 'name': 'Depreciation', 'name_cn': '折旧费用',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '6000', 'is_system': False},
        {'code': '6900', 'name': 'Other Expenses', 'name_cn': '其他费用',
         'account_type': 'expense', 'balance_direction': 'debit', 'level': 2, 'parent_code': '6000', 'is_system': False},
    ]

    # 清空现有数据（可选，谨慎使用）
    # ChartOfAccount.query.delete()
    # db.session.commit()

    # 第一轮：创建所有科目（不设置parent_id）
    code_to_account = {}
    created_count = 0
    skipped_count = 0

    for acc_data in accounts_data:
        existing = ChartOfAccount.query.filter_by(code=acc_data['code']).first()
        if existing:
            code_to_account[acc_data['code']] = existing
            skipped_count += 1
            print(f"  跳过已存在: {acc_data['code']} - {acc_data['name']}")
        else:
            parent_code = acc_data.pop('parent_code', None)
            account = ChartOfAccount(**acc_data)
            account._pending_parent_code = parent_code
            db.session.add(account)
            code_to_account[acc_data['code']] = account
            created_count += 1
            print(f"  创建科目: {acc_data['code']} - {acc_data['name']} ({acc_data['name_cn']})")

    db.session.flush()

    # 第二轮：设置parent_id
    for code, account in code_to_account.items():
        if hasattr(account, '_pending_parent_code') and account._pending_parent_code:
            parent = code_to_account.get(account._pending_parent_code)
            if parent:
                account.parent_id = parent.id
            delattr(account, '_pending_parent_code')

    db.session.commit()

    print()
    print("=" * 60)
    print(f"初始化完成！")
    print(f"  - 新建科目: {created_count} 个")
    print(f"  - 跳过已存在: {skipped_count} 个")
    print(f"  - 科目总数: {ChartOfAccount.query.count()} 个")
    print("=" * 60)

    # 显示科目树
    print()
    print("会计科目表:")
    print("-" * 60)
    accounts = ChartOfAccount.query.order_by(ChartOfAccount.code).all()
    for acc in accounts:
        indent = "  " * (acc.level - 1)
        print(f"{indent}{acc.code} | {acc.name} | {acc.name_cn}")
    print("-" * 60)


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='初始化会计科目表')
    parser.add_argument('--execute', action='store_true', help='执行初始化')
    args = parser.parse_args()

    if not args.execute:
        print("此脚本将初始化旅行社业务所需的会计科目表")
        print()
        print("会计科目结构预览:")
        print("  1xxx - 资产类 (Assets)")
        print("    1001 现金 / 1002-1004 银行存款")
        print("    1100 应收账款 / 1200 预付账款")
        print("  2xxx - 负债类 (Liabilities)")
        print("    2100 应付账款 / 2200 预收账款")
        print("  3xxx - 权益类 (Equity)")
        print("    3100 股本 / 3200 留存收益")
        print("  4xxx - 收入类 (Revenue)")
        print("    4100 销售收入 (机票/旅游/签证/酒店/用车)")
        print("    4200 佣金收入")
        print("  5xxx - 成本类 (Cost of Sales)")
        print("    5100 直接成本 (机票/旅游/签证/酒店/用车)")
        print("  6xxx - 费用类 (Operating Expenses)")
        print("    6100-6900 工资/租金/水电/推广/办公等")
        print()
        print("使用 --execute 参数执行初始化")
        print("示例: python scripts/20260110_init_chart_of_accounts.py --execute")
        return

    from App_new import create_app
    app = create_app()
    with app.app_context():
        init_chart_of_accounts()


if __name__ == '__main__':
    main()

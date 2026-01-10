# -*- coding: utf-8 -*-
"""
初始化会计科目表脚本
创建日期: 2026-01-10
说明: 初始化 Ledger 系统所需的默认会计科目
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.finance.models.chart_of_account import ChartOfAccount


def init_accounts():
    """初始化默认会计科目"""
    print("=" * 60)
    print("初始化会计科目表")
    print("=" * 60)

    # 检查是否已有科目
    existing_count = ChartOfAccount.query.count()
    if existing_count > 0:
        print(f"已存在 {existing_count} 个会计科目")

        # 检查关键科目是否存在
        required_codes = ['1002', '1100', '4100', '5100']
        missing_codes = []
        for code in required_codes:
            if not ChartOfAccount.get_by_code(code):
                missing_codes.append(code)

        if missing_codes:
            print(f"缺少关键科目: {', '.join(missing_codes)}")
            print("正在初始化默认科目...")
            ChartOfAccount.init_default_accounts()
            print("默认科目初始化完成！")
        else:
            print("所有关键科目已存在，无需初始化")
    else:
        print("会计科目表为空，正在初始化默认科目...")
        ChartOfAccount.init_default_accounts()
        print("默认科目初始化完成！")

    # 显示当前科目列表
    accounts = ChartOfAccount.query.order_by(ChartOfAccount.code).all()
    print("\n当前会计科目列表:")
    print("-" * 60)
    for acc in accounts:
        indent = "  " * (acc.level - 1)
        print(f"{indent}{acc.code} - {acc.name} ({acc.name_cn or '-'})")
    print("-" * 60)
    print(f"共 {len(accounts)} 个科目")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='初始化会计科目表')
    parser.add_argument('--execute', action='store_true', help='执行初始化')
    args = parser.parse_args()

    if not args.execute:
        print("使用 --execute 参数执行初始化")
        print("示例: python scripts/20260110_init_ledger_accounts.py --execute")
        return

    app = create_app()
    with app.app_context():
        init_accounts()


if __name__ == '__main__':
    main()

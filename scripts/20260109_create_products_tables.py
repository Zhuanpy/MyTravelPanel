# -*- coding: utf-8 -*-
"""
创建统一产品系统数据库表
运行方式: python scripts/20260109_create_products_tables.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def create_tables():
    """创建统一产品系统的所有表"""
    app = create_app()

    with app.app_context():
        # 导入所有模型以确保它们被注册
        from App_new.business.products.models import (
            ProductsUnified,
            ProductsPrice,
            ProductsRule,
            ProductsTicketExt,
            ProductsCarExt,
            ProductsCruiseExt,
            ProductsHotelExt,
            ProductsInsuranceExt,
            ProductsVisaExt,
        )

        # 要创建的表列表
        tables_to_create = [
            ProductsUnified.__table__,
            ProductsPrice.__table__,
            ProductsRule.__table__,
            ProductsTicketExt.__table__,
            ProductsCarExt.__table__,
            ProductsCruiseExt.__table__,
            ProductsHotelExt.__table__,
            ProductsInsuranceExt.__table__,
            ProductsVisaExt.__table__,
        ]

        print("=" * 60)
        print("统一产品系统 - 数据库表创建脚本")
        print("=" * 60)

        # 检查现有表
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        print("\n现有表:")
        for table in tables_to_create:
            status = "[OK] 已存在" if table.name in existing_tables else "[--] 不存在"
            print(f"  - {table.name}: {status}")

        # 确认创建
        print("\n即将创建以下表（如果不存在）:")
        for table in tables_to_create:
            if table.name not in existing_tables:
                print(f"  - {table.name}")

        # 自动确认或交互确认
        import sys
        if '--yes' in sys.argv or '-y' in sys.argv:
            confirm = 'y'
        else:
            confirm = input("\n是否继续? (y/n): ")
        if confirm.lower() != 'y':
            print("已取消操作")
            return

        # 创建表
        print("\n开始创建表...")

        try:
            # 只创建不存在的表
            db.create_all()

            print("\n创建完成！")

            # 验证创建结果
            inspector = inspect(db.engine)
            new_tables = inspector.get_table_names()

            print("\n验证结果:")
            for table in tables_to_create:
                status = "[OK] 成功" if table.name in new_tables else "[!!] 失败"
                print(f"  - {table.name}: {status}")

        except Exception as e:
            print(f"\n创建表时出错: {str(e)}")
            db.session.rollback()
            raise

        print("\n" + "=" * 60)
        print("数据库表创建完成！")
        print("=" * 60)


def show_table_info():
    """显示表结构信息"""
    app = create_app()

    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)

        tables = [
            'products_unified',
            'products_price',
            'products_rule',
            'products_ticket_ext',
            'products_car_ext',
            'products_cruise_ext',
            'products_hotel_ext',
            'products_insurance_ext',
            'products_visa_ext',
        ]

        print("=" * 60)
        print("统一产品系统 - 表结构信息")
        print("=" * 60)

        for table_name in tables:
            if table_name in inspector.get_table_names():
                print(f"\n【{table_name}】")
                columns = inspector.get_columns(table_name)
                for col in columns:
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    print(f"  - {col['name']}: {col['type']} {nullable}")
            else:
                print(f"\n【{table_name}】- 表不存在")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='统一产品系统数据库管理')
    parser.add_argument('--info', action='store_true', help='显示表结构信息')
    parser.add_argument('--create', action='store_true', help='创建数据库表')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认（跳过确认提示）')

    args = parser.parse_args()

    if args.info:
        show_table_info()
    elif args.create:
        create_tables()
    else:
        # 默认创建表
        create_tables()

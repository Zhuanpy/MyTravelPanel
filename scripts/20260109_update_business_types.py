# -*- coding: utf-8 -*-
"""
更新 business_types 表，添加产品编号前缀字段
运行方式: python scripts/20260109_update_business_types.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def update_business_types():
    """更新 business_types 表结构和数据"""
    app = create_app()

    with app.app_context():
        from sqlalchemy import inspect, text

        print("=" * 60)
        print("更新 business_types 表")
        print("=" * 60)

        inspector = inspect(db.engine)

        # 检查表是否存在
        if 'business_types' not in inspector.get_table_names():
            print("[!!] business_types 表不存在")
            return

        # 获取现有列
        columns = [col['name'] for col in inspector.get_columns('business_types')]
        print(f"\n现有列: {columns}")

        # 添加新列
        new_columns = []

        if 'name_en' not in columns:
            new_columns.append("ADD COLUMN name_en VARCHAR(100) COMMENT '英文名称'")
            print("[--] 需要添加 name_en 列")

        if 'product_code_prefix' not in columns:
            new_columns.append("ADD COLUMN product_code_prefix VARCHAR(5) COMMENT '产品编号前缀'")
            print("[--] 需要添加 product_code_prefix 列")

        if new_columns:
            try:
                alter_sql = f"ALTER TABLE business_types {', '.join(new_columns)}"
                print(f"\n执行: {alter_sql}")
                db.session.execute(text(alter_sql))
                db.session.commit()
                print("[OK] 列添加成功")
            except Exception as e:
                print(f"[!!] 添加列失败: {e}")
                db.session.rollback()
                return
        else:
            print("[OK] 所有列已存在")

        # 更新数据
        print("\n更新产品编号前缀数据...")

        prefix_mapping = {
            'flight': ('Flight', 'FLT'),
            'hotel': ('Hotel', 'HTL'),
            'visa': ('Visa', 'VIS'),
            'tour': ('Tour', 'TOU'),
            'insurance': ('Insurance', 'INS'),
            'transport': ('Transport', 'TRP'),
            'attraction': ('Attraction', 'ATR'),
            'car': ('Car Rental', 'CAR'),
            'cruise': ('Cruise', 'CRU'),
            'ferry': ('Ferry', 'FRY'),
            'land_tour': ('Land Tour', 'LND'),
            'rail_coach': ('Rail/Coach', 'TRN'),
            'service_fee': ('Service Fee', 'SVC'),
            'ticket': ('Ticket', 'TKT'),
            'transfer': ('Transfer', 'TRF'),
            'tour_package': ('Tour Package', 'PKG'),
            'voucher': ('Voucher', 'VOU'),
            'other': ('Other', 'OTH'),
        }

        from App_new.shared.models.business_types import BusinessType

        updated_count = 0
        for code, (name_en, prefix) in prefix_mapping.items():
            bt = BusinessType.query.filter_by(code=code).first()
            if bt:
                bt.name_en = name_en
                bt.product_code_prefix = prefix
                updated_count += 1
                print(f"  [OK] {code}: {name_en} -> {prefix}")

        db.session.commit()
        print(f"\n更新完成: {updated_count} 条记录")

        # 显示结果
        print("\n" + "=" * 60)
        print("产品编号前缀配置")
        print("=" * 60)
        print(f"{'代码':<15} {'中文名':<12} {'英文名':<15} {'前缀':<5}")
        print("-" * 50)

        all_types = BusinessType.query.order_by(BusinessType.sort_order).all()
        for bt in all_types:
            print(f"{bt.code:<15} {bt.name:<12} {bt.name_en or '-':<15} {bt.product_code_prefix or '-':<5}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='更新业务类型产品编号前缀')
    parser.add_argument('--execute', action='store_true', help='执行更新')
    parser.add_argument('--info', action='store_true', help='仅显示当前配置')

    args = parser.parse_args()

    if args.info:
        # 仅显示当前配置
        app = create_app()
        with app.app_context():
            from App_new.shared.models.business_types import BusinessType
            print("当前产品编号前缀配置:")
            print(f"{'代码':<15} {'中文名':<12} {'英文名':<15} {'前缀':<5}")
            print("-" * 50)
            all_types = BusinessType.query.order_by(BusinessType.sort_order).all()
            for bt in all_types:
                print(f"{bt.code:<15} {bt.name:<12} {bt.name_en or '-':<15} {bt.product_code_prefix or '-':<5}")
    elif args.execute:
        update_business_types()
    else:
        print("使用 --execute 执行更新，或 --info 查看当前配置")

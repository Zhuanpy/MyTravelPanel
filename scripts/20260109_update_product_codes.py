# -*- coding: utf-8 -*-
"""
更新产品编号为新格式
格式: {3字母前缀}-{年月}-{序号}
例如: TOU-2601-001

运行方式: python scripts/20260109_update_product_codes.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def update_product_codes(dry_run=True):
    """更新产品编号"""
    app = create_app()

    with app.app_context():
        from App_new.business.products.models import ProductsUnified, ProductCategory
        from App_new.business.tour.models.Packagemodels import Product
        from App_new.shared.models.business_types import BusinessType

        print("=" * 60)
        print("更新产品编号为新格式")
        print("=" * 60)

        if dry_run:
            print("[预览模式] 不会实际修改数据\n")
        else:
            print("[执行模式] 将更新数据库\n")

        # 前缀映射 (旧 -> 新)
        prefix_mapping = {
            'TOUR': 'TOU',
            'VISA': 'VIS',
            'TICKET': 'TKT',
            'TKT': 'TKT',
            'CAR': 'CAR',
            'CRUISE': 'CRU',
            'CRU': 'CRU',
            'HOTEL': 'HTL',
            'HTL': 'HTL',
            'FLIGHT': 'FLT',
            'FLT': 'FLT',
            'INSURANCE': 'INS',
            'INS': 'INS',
        }

        # ========== 更新统一产品表 ==========
        print("1. 更新统一产品表 (products_unified)")
        print("-" * 40)

        unified_products = ProductsUnified.query.all()
        unified_updated = 0

        for product in unified_products:
            old_code = product.product_code
            if not old_code:
                continue

            # 检查是否需要更新 (格式: PREFIX-YYMM-SEQ)
            parts = old_code.split('-')
            if len(parts) == 3:
                old_prefix = parts[0]
                if old_prefix in prefix_mapping and old_prefix != prefix_mapping[old_prefix]:
                    new_prefix = prefix_mapping[old_prefix]
                    new_code = f"{new_prefix}-{parts[1]}-{parts[2]}"

                    if dry_run:
                        print(f"  [预览] {old_code} -> {new_code}")
                    else:
                        product.product_code = new_code
                        print(f"  [更新] {old_code} -> {new_code}")

                    unified_updated += 1

        if not dry_run and unified_updated > 0:
            db.session.commit()

        print(f"\n统一产品表: {'将更新' if dry_run else '已更新'} {unified_updated} 条记录")

        # ========== 更新旅游产品表 ==========
        print("\n2. 更新旅游产品表 (package_products)")
        print("-" * 40)

        tour_products = Product.query.all()
        tour_updated = 0

        # 按年月分组计数
        seq_counters = {}

        for product in tour_products:
            old_code = product.product_code

            # 检查是否已经是新格式
            if old_code and old_code.startswith('TOU-'):
                continue

            # 生成新编号
            from datetime import datetime
            year_month = datetime.now().strftime('%y%m')

            # 获取序号
            key = f"TOU-{year_month}"
            if key not in seq_counters:
                # 查找当前最大序号
                max_product = Product.query.filter(
                    Product.product_code.like(f'{key}-%')
                ).order_by(Product.product_code.desc()).first()

                if max_product and max_product.product_code:
                    try:
                        last_seq = int(max_product.product_code.split('-')[-1])
                        seq_counters[key] = last_seq
                    except:
                        seq_counters[key] = 0
                else:
                    seq_counters[key] = 0

            seq_counters[key] += 1
            new_code = f"{key}-{seq_counters[key]:03d}"

            if dry_run:
                print(f"  [预览] {old_code or '(空)'} -> {new_code}")
            else:
                product.product_code = new_code
                print(f"  [更新] {old_code or '(空)'} -> {new_code}")

            tour_updated += 1

        if not dry_run and tour_updated > 0:
            db.session.commit()

        print(f"\n旅游产品表: {'将更新' if dry_run else '已更新'} {tour_updated} 条记录")

        # ========== 同步更新关联 ==========
        if not dry_run:
            print("\n3. 同步统一产品表中的旅游产品编号")
            print("-" * 40)

            # 重新同步旅游产品到统一表
            synced = 0
            for product in Product.query.all():
                unified = ProductsUnified.query.filter_by(
                    product_category=ProductCategory.TOUR,
                    ext_table_id=product.id
                ).first()

                if unified and unified.product_code != product.product_code:
                    # 保留统一表的编号格式，不使用旅游表的编号
                    pass

            print(f"同步完成")

        # ========== 汇总 ==========
        print("\n" + "=" * 60)
        print("更新汇总")
        print("=" * 60)
        print(f"统一产品表: {unified_updated} 条")
        print(f"旅游产品表: {tour_updated} 条")

        if dry_run:
            print("\n要实际执行更新，请使用 --execute 参数")


def show_current_codes():
    """显示当前编号情况"""
    app = create_app()

    with app.app_context():
        from App_new.business.products.models import ProductsUnified
        from App_new.business.tour.models.Packagemodels import Product
        from sqlalchemy import func

        print("=" * 60)
        print("当前产品编号统计")
        print("=" * 60)

        # 统一产品表
        print("\n统一产品表 (products_unified):")
        results = db.session.query(
            func.left(ProductsUnified.product_code, 4).label('prefix'),
            func.count().label('count')
        ).group_by('prefix').all()

        for prefix, count in results:
            print(f"  {prefix or '(空)'}: {count} 条")

        # 旅游产品表
        print("\n旅游产品表 (package_products):")
        results = db.session.query(
            func.left(Product.product_code, 4).label('prefix'),
            func.count().label('count')
        ).group_by('prefix').all()

        for prefix, count in results:
            print(f"  {prefix or '(空)'}: {count} 条")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='更新产品编号')
    parser.add_argument('--execute', action='store_true', help='实际执行更新')
    parser.add_argument('--show', action='store_true', help='显示当前编号情况')

    args = parser.parse_args()

    if args.show:
        show_current_codes()
    else:
        update_product_codes(dry_run=not args.execute)

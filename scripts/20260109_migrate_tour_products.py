# -*- coding: utf-8 -*-
"""
迁移旅游产品数据到统一产品表
运行方式: python scripts/20260109_migrate_tour_products.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def migrate_tour_products(dry_run=True):
    """
    迁移旅游产品到统一产品表

    Args:
        dry_run: 如果为True，只显示将要迁移的数据，不实际执行
    """
    app = create_app()

    with app.app_context():
        # 导入模型
        from App_new.business.tour.models.Packagemodels import Product
        from App_new.business.products.models import (
            ProductsUnified,
            ProductCategory,
            ProductSubCategory,
            ProductsPrice,
            PeopleType
        )

        print("=" * 60)
        print("旅游产品数据迁移脚本")
        print("=" * 60)

        # 查询所有旅游产品
        tour_products = Product.query.all()
        print(f"\n找到 {len(tour_products)} 个旅游产品")

        if not tour_products:
            print("没有需要迁移的旅游产品")
            return

        # 检查是否已经迁移过
        existing_count = ProductsUnified.query.filter_by(
            product_category=ProductCategory.TOUR
        ).count()

        if existing_count > 0:
            print(f"\n警告: 统一产品表中已存在 {existing_count} 个旅游产品")
            import sys
            if '--yes' in sys.argv or '-y' in sys.argv:
                confirm = 'y'
            else:
                confirm = input("是否继续迁移？(y/n): ")
            if confirm.lower() != 'y':
                print("已取消操作")
                return

        # 产品类型映射
        product_type_map = {
            '跟团游': ProductSubCategory.TOUR_GROUP,
            '自由行': ProductSubCategory.TOUR_FREE,
            '定制游': ProductSubCategory.TOUR_CUSTOM,
            '当地游': ProductSubCategory.TOUR_LOCAL,
        }

        migrated_count = 0
        error_count = 0

        print("\n开始迁移...")

        for product in tour_products:
            try:
                # 检查是否已迁移（通过ext_table_id）
                existing = ProductsUnified.query.filter_by(
                    product_category=ProductCategory.TOUR,
                    ext_table_id=product.id
                ).first()

                if existing:
                    print(f"  跳过: {product.product_name} (已迁移)")
                    continue

                # 映射产品子类
                sub_category = product_type_map.get(
                    product.product_type,
                    ProductSubCategory.TOUR_GROUP  # 默认跟团游
                )

                # 生成产品编号 - 总是生成新的编号以避免冲突
                product_code = ProductsUnified.generate_product_code(ProductCategory.TOUR)

                # 获取国家信息
                country = None
                city = None
                if product.city:
                    country = product.city.country_name
                    city = product.city.city_name

                if dry_run:
                    print(f"  [预览] {product.product_name}")
                    print(f"         编号: {product_code}")
                    print(f"         类型: {product.product_type} -> {sub_category}")
                    print(f"         价格: {product.base_price} {product.currency}")
                    continue

                # 创建统一产品记录
                unified = ProductsUnified(
                    product_code=product_code,
                    product_name=product.product_name,
                    product_category=ProductCategory.TOUR,
                    product_sub_category=sub_category,
                    sale_type='service',
                    product_status=product.product_status or 'draft',
                    is_featured=product.is_featured or False,
                    is_hot=False,
                    is_new=False,
                    supplier_id=product.supplier_id,
                    country=country,
                    city=city,
                    departure_city=product.departure_city,
                    destination=product.destination_city,
                    base_price=product.base_price,
                    currency=product.currency or 'SGD',
                    cover_image=product.cover_image,
                    gallery_images=product.gallery_images,
                    short_description=product.highlights[:500] if product.highlights else None,
                    description=product.product_description,
                    highlights=product.highlights,
                    includes=product.included_services,
                    excludes=product.excluded_services,
                    important_notes=product.important_notes,
                    valid_from=product.valid_from,
                    valid_until=product.valid_until,
                    tags=product.tags,
                    ext_table_id=product.id,  # 关联原表
                    created_by=product.created_by,
                )

                db.session.add(unified)
                db.session.flush()  # 获取ID

                # 创建价格记录
                if product.base_price:
                    adult_price = ProductsPrice(
                        product_id=unified.id,
                        price_type='standard',
                        price_name='成人价',
                        people_type=PeopleType.ADULT,
                        selling_price=product.base_price,
                        currency=product.currency or 'SGD',
                        is_active=True,
                    )
                    db.session.add(adult_price)

                if product.child_price:
                    child_price = ProductsPrice(
                        product_id=unified.id,
                        price_type='standard',
                        price_name='儿童价',
                        people_type=PeopleType.CHILD,
                        selling_price=product.child_price,
                        currency=product.currency or 'SGD',
                        is_active=True,
                    )
                    db.session.add(child_price)

                if product.infant_price:
                    infant_price = ProductsPrice(
                        product_id=unified.id,
                        price_type='standard',
                        price_name='婴儿价',
                        people_type=PeopleType.INFANT,
                        selling_price=product.infant_price,
                        currency=product.currency or 'SGD',
                        is_active=True,
                    )
                    db.session.add(infant_price)

                # 每个产品单独提交，避免一个失败导致全部回滚
                db.session.commit()
                migrated_count += 1
                print(f"  [OK] 迁移成功: {product.product_name}")

            except Exception as e:
                error_count += 1
                print(f"  [!!] 迁移失败: {product.product_name} - {str(e)}")
                db.session.rollback()

        if not dry_run:
            print(f"\n迁移完成: 成功 {migrated_count} 个, 失败 {error_count} 个")
        else:
            print(f"\n[预览模式] 将迁移 {len(tour_products)} 个产品")
            print("要实际执行迁移，请使用 --execute 参数")


def verify_migration():
    """验证迁移结果"""
    app = create_app()

    with app.app_context():
        from App_new.business.tour.models.Packagemodels import Product
        from App_new.business.products.models import ProductsUnified, ProductCategory

        print("=" * 60)
        print("迁移验证")
        print("=" * 60)

        # 统计原表
        original_count = Product.query.count()
        print(f"\n原旅游产品表 (package_products): {original_count} 条")

        # 统计新表
        migrated_count = ProductsUnified.query.filter_by(
            product_category=ProductCategory.TOUR
        ).count()
        print(f"统一产品表 (products_unified): {migrated_count} 条旅游产品")

        # 检查关联
        unlinked = ProductsUnified.query.filter(
            ProductsUnified.product_category == ProductCategory.TOUR,
            ProductsUnified.ext_table_id == None
        ).count()

        if unlinked > 0:
            print(f"\n警告: {unlinked} 个产品未关联原表")

        # 显示示例
        print("\n最近迁移的产品:")
        recent = ProductsUnified.query.filter_by(
            product_category=ProductCategory.TOUR
        ).order_by(ProductsUnified.created_at.desc()).limit(5).all()

        for p in recent:
            print(f"  - {p.product_code}: {p.product_name}")
            print(f"    原表ID: {p.ext_table_id}, 状态: {p.product_status}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='旅游产品数据迁移')
    parser.add_argument('--execute', action='store_true', help='实际执行迁移（默认为预览模式）')
    parser.add_argument('--verify', action='store_true', help='验证迁移结果')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认')

    args = parser.parse_args()

    if args.verify:
        verify_migration()
    else:
        migrate_tour_products(dry_run=not args.execute)

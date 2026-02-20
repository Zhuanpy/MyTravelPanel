# -*- coding: utf-8 -*-
"""
迁移脚本：重新同步旅游产品的基础价格和成本价到统一产品表
原因：旅游产品价格现在存储在 price_variant 表中，而非 base_price 字段
运行方式：python scripts/20260219_resync_tour_base_price.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.products.models import ProductsUnified, ProductCategory
from App_new.business.products.sync_helper import _get_tour_base_price, _get_tour_cost_price

app = create_app()

with app.app_context():
    try:
        # 查找所有旅游类的统一产品
        tour_products = ProductsUnified.query.filter_by(
            product_category=ProductCategory.TOUR
        ).all()

        updated = 0
        for unified in tour_products:
            if not unified.ext_table_id:
                continue

            # 获取对应的旅游产品
            from App_new.business.tour.models.Packagemodels import Product as PackageProduct
            tour = PackageProduct.query.get(unified.ext_table_id)
            if not tour:
                continue

            changed = False

            # 同步售价
            base_price = _get_tour_base_price(tour)
            if base_price and base_price != unified.base_price:
                print(f"  [{unified.product_code}] 售价: {unified.base_price} -> {base_price}")
                unified.base_price = base_price
                changed = True

            # 同步成本
            cost_price = _get_tour_cost_price(tour)
            if cost_price and cost_price != unified.cost_price:
                print(f"  [{unified.product_code}] 成本: {unified.cost_price} -> {cost_price}")
                unified.cost_price = cost_price
                changed = True

            if changed:
                updated += 1

        if updated > 0:
            db.session.commit()
            print(f"\n成功更新 {updated} 个产品")
        else:
            print("没有需要更新的产品")

    except Exception as e:
        db.session.rollback()
        print(f"迁移失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将现有签证类型同步到统一产品系统

运行方式: python scripts/20260201_sync_visa_to_products.py

此脚本会：
1. 遍历所有 VisaTypes 记录
2. 为每个签证类型创建对应的 ProductsUnified 和 ProductsVisaExt 记录
3. 同步相关字段（名称、价格、状态等）
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from App_new.business.visa.models.Visamodels import VisaTypes
from App_new.business.products.models import ProductsUnified
from App_new.business.products.models.products_visa_ext import ProductsVisaExt
from App_new.business.products.services.visa_sync_service import VisaSyncService


def check_existing_sync():
    """检查已同步的记录数量"""
    synced_count = ProductsVisaExt.query.filter(
        ProductsVisaExt.visa_type_id.isnot(None)
    ).count()
    total_visa_types = VisaTypes.query.count()
    return synced_count, total_visa_types


def sync_all():
    """同步所有签证类型"""
    print("=" * 60)
    print("签证类型同步到统一产品系统")
    print("=" * 60)

    # 检查现有状态
    synced_count, total_count = check_existing_sync()
    print(f"\n当前状态:")
    print(f"  - 签证类型总数: {total_count}")
    print(f"  - 已同步数量: {synced_count}")
    print(f"  - 待同步数量: {total_count - synced_count}")

    if synced_count == total_count:
        print("\n所有签证类型已同步，无需操作。")
        return

    # 确认执行
    confirm = input("\n是否继续同步？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消操作。")
        return

    print("\n开始同步...")

    # 获取所有签证类型
    visa_types = VisaTypes.query.all()
    success_count = 0
    error_count = 0
    skip_count = 0

    for vt in visa_types:
        try:
            # 检查是否已同步
            existing = ProductsVisaExt.query.filter_by(visa_type_id=vt.id).first()
            if existing:
                print(f"  [跳过] {vt.visa_type} - 已存在关联产品")
                skip_count += 1
                continue

            # 执行同步
            product = VisaSyncService.sync_visa_type_to_product(vt)
            print(f"  [成功] {vt.visa_type} -> {product.product_code}")
            success_count += 1

        except Exception as e:
            print(f"  [失败] {vt.visa_type} - 错误: {str(e)}")
            error_count += 1

    # 提交事务
    try:
        db.session.commit()
        print("\n事务提交成功！")
    except Exception as e:
        db.session.rollback()
        print(f"\n事务提交失败: {str(e)}")
        return

    # 输出统计
    print("\n" + "=" * 60)
    print("同步完成！")
    print("=" * 60)
    print(f"  - 成功同步: {success_count}")
    print(f"  - 跳过已存在: {skip_count}")
    print(f"  - 失败: {error_count}")

    # 验证结果
    final_synced, _ = check_existing_sync()
    print(f"\n最终同步状态: {final_synced}/{total_count}")


def verify_sync():
    """验证同步结果"""
    print("\n验证同步结果...")
    print("-" * 60)

    # 获取所有签证类型
    visa_types = VisaTypes.query.all()

    for vt in visa_types:
        ext = ProductsVisaExt.query.filter_by(visa_type_id=vt.id).first()
        if ext:
            product = ext.product
            status = "已同步"
            product_info = f"{product.product_code} | {product.product_name}"
        else:
            status = "未同步"
            product_info = "-"

        print(f"  [{status}] {vt.visa_type} -> {product_info}")


def main():
    app = create_app()
    with app.app_context():
        print("\n初始化数据库连接...")

        # 显示菜单
        print("\n请选择操作:")
        print("  1. 同步所有签证类型")
        print("  2. 验证同步结果")
        print("  3. 退出")

        choice = input("\n请输入选项 (1/2/3): ").strip()

        if choice == '1':
            sync_all()
        elif choice == '2':
            verify_sync()
        elif choice == '3':
            print("退出程序。")
        else:
            print("无效选项。")


if __name__ == '__main__':
    main()

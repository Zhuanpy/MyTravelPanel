# -*- coding: utf-8 -*-
"""
迁移签证产品数据到统一产品表
运行方式: python scripts/20260109_migrate_visa_products.py
"""

import sys
import os
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db


def parse_fee(fee_str):
    """解析费用字符串，提取数字"""
    if not fee_str:
        return None
    try:
        # 提取数字（包括小数）
        numbers = re.findall(r'[\d.]+', str(fee_str))
        if numbers:
            return float(numbers[0])
    except (ValueError, TypeError):
        pass
    return None


def migrate_visa_products(dry_run=True):
    """
    迁移签证产品到统一产品表

    Args:
        dry_run: 如果为True，只显示将要迁移的数据，不实际执行
    """
    app = create_app()

    with app.app_context():
        # 导入模型
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries
        from App_new.business.products.models import (
            ProductsUnified,
            ProductCategory,
            ProductsVisaExt,
            VisaCategory,
        )

        print("=" * 60)
        print("签证产品数据迁移脚本")
        print("=" * 60)

        # 查询所有签证类型
        visa_types = VisaTypes.query.all()
        print(f"\n找到 {len(visa_types)} 个签证类型")

        if not visa_types:
            print("没有需要迁移的签证产品")
            return

        # 检查是否已经迁移过
        existing_count = ProductsUnified.query.filter_by(
            product_category=ProductCategory.VISA
        ).count()

        if existing_count > 0:
            print(f"\n警告: 统一产品表中已存在 {existing_count} 个签证产品")
            if '--yes' in sys.argv or '-y' in sys.argv:
                confirm = 'y'
            else:
                confirm = input("是否继续迁移？(y/n): ")
            if confirm.lower() != 'y':
                print("已取消操作")
                return

        # 签证类型映射
        visa_category_map = {
            '旅游签证': VisaCategory.TOURIST,
            '商务签证': VisaCategory.BUSINESS,
            '学生签证': VisaCategory.STUDENT,
            '工作签证': VisaCategory.WORK,
            '过境签证': VisaCategory.TRANSIT,
            '探亲签证': VisaCategory.FAMILY,
        }

        migrated_count = 0
        error_count = 0

        print("\n开始迁移...")

        for visa_type in visa_types:
            try:
                # 检查是否已迁移
                existing = ProductsUnified.query.filter_by(
                    product_category=ProductCategory.VISA,
                    ext_table_id=visa_type.id
                ).first()

                if existing:
                    print(f"  跳过: {visa_type.visa_type} (已迁移)")
                    continue

                # 获取国家信息
                country = visa_type.country
                country_name = country.country_name_CN if country else '未知'
                country_name_en = country.country_name_EN if country else None
                country_code = country.country_code if country else None

                # 生成产品名称和编号
                product_name = f"{country_name}{visa_type.visa_type}"
                product_code = f"VISA-{country_code or 'XX'}-{visa_type.id:04d}"

                # 解析费用
                total_fee = parse_fee(visa_type.fee)

                # 判断签证类别
                visa_category = VisaCategory.TOURIST  # 默认旅游签证
                visa_type_lower = visa_type.visa_type.lower() if visa_type.visa_type else ''
                for keyword, category in visa_category_map.items():
                    if keyword in visa_type.visa_type:
                        visa_category = category
                        break

                if dry_run:
                    print(f"  [预览] {product_name}")
                    print(f"         编号: {product_code}")
                    print(f"         国家: {country_name} ({country_code})")
                    print(f"         费用: {visa_type.fee} -> {total_fee}")
                    print(f"         处理时间: {visa_type.processing_time}")
                    continue

                # 创建统一产品记录
                unified = ProductsUnified(
                    product_code=product_code,
                    product_name=product_name,
                    product_short_name=visa_type.visa_type,
                    product_category=ProductCategory.VISA,
                    product_sub_category=visa_category,
                    sale_type='service',
                    product_status='active' if visa_type.is_active else 'inactive',
                    is_hot=False,
                    is_featured=False,
                    is_new=False,
                    country=country_name,
                    city=None,
                    base_price=total_fee,
                    currency='SGD',
                    description=visa_type.introduction,
                    valid_until=visa_type.valid_until.date() if visa_type.valid_until else None,
                    ext_table_id=visa_type.id,  # 关联原表
                )

                db.session.add(unified)
                db.session.flush()  # 获取ID

                # 创建签证扩展记录
                visa_ext = ProductsVisaExt(
                    product_id=unified.id,
                    visa_type_id=visa_type.id,
                    country_id=visa_type.country_id,
                    visa_category=visa_category,
                    visa_name=visa_type.visa_type,
                    destination_country=country_name,
                    destination_country_en=country_name_en,
                    destination_country_code=country_code,
                    processing_time=visa_type.processing_time,
                    total_fee=total_fee,
                    fee_currency='SGD',
                    important_notes=visa_type.introduction,
                )

                db.session.add(visa_ext)

                # 每个产品单独提交
                db.session.commit()
                migrated_count += 1
                print(f"  [OK] 迁移成功: {product_name}")

            except Exception as e:
                error_count += 1
                print(f"  [!!] 迁移失败: {visa_type.visa_type} - {str(e)}")
                db.session.rollback()

        if not dry_run:
            print(f"\n迁移完成: 成功 {migrated_count} 个, 失败 {error_count} 个")
        else:
            print(f"\n[预览模式] 将迁移 {len(visa_types)} 个签证产品")
            print("要实际执行迁移，请使用 --execute 参数")


def verify_migration():
    """验证迁移结果"""
    app = create_app()

    with app.app_context():
        from App_new.business.visa.models.Visamodels import VisaTypes
        from App_new.business.products.models import (
            ProductsUnified,
            ProductCategory,
            ProductsVisaExt
        )

        print("=" * 60)
        print("迁移验证")
        print("=" * 60)

        # 统计原表
        original_count = VisaTypes.query.count()
        print(f"\n原签证类型表 (visa_types): {original_count} 条")

        # 统计新表
        migrated_count = ProductsUnified.query.filter_by(
            product_category=ProductCategory.VISA
        ).count()
        print(f"统一产品表 (products_unified): {migrated_count} 条签证产品")

        # 统计扩展表
        ext_count = ProductsVisaExt.query.count()
        print(f"签证扩展表 (products_visa_ext): {ext_count} 条")

        # 检查关联
        unlinked = ProductsUnified.query.filter(
            ProductsUnified.product_category == ProductCategory.VISA,
            ProductsUnified.ext_table_id == None
        ).count()

        if unlinked > 0:
            print(f"\n警告: {unlinked} 个产品未关联原表")

        # 显示示例
        print("\n最近迁移的签证产品:")
        recent = ProductsUnified.query.filter_by(
            product_category=ProductCategory.VISA
        ).order_by(ProductsUnified.created_at.desc()).limit(5).all()

        for p in recent:
            print(f"  - {p.product_code}: {p.product_name}")
            print(f"    价格: {p.base_price} {p.currency}, 状态: {p.product_status}")

            # 显示扩展信息
            if p.visa_ext:
                print(f"    处理时间: {p.visa_ext.processing_time}")


def list_visa_types():
    """列出所有签证类型"""
    app = create_app()

    with app.app_context():
        from App_new.business.visa.models.Visamodels import VisaTypes

        print("=" * 60)
        print("现有签证类型列表")
        print("=" * 60)

        visa_types = VisaTypes.query.all()

        for vt in visa_types:
            country = vt.country
            country_name = country.country_name_CN if country else '未知'
            status = '[OK] 激活' if vt.is_active else '[--] 停用'

            print(f"\n[{vt.id}] {country_name} - {vt.visa_type}")
            print(f"    费用: {vt.fee}")
            print(f"    处理时间: {vt.processing_time}")
            print(f"    状态: {status}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='签证产品数据迁移')
    parser.add_argument('--execute', action='store_true', help='实际执行迁移（默认为预览模式）')
    parser.add_argument('--verify', action='store_true', help='验证迁移结果')
    parser.add_argument('--list', action='store_true', help='列出所有签证类型')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认')

    args = parser.parse_args()

    if args.verify:
        verify_migration()
    elif args.list:
        list_visa_types()
    else:
        migrate_visa_products(dry_run=not args.execute)

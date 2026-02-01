# -*- coding: utf-8 -*-
"""
签证产品同步服务
实现 VisaTypes 与 ProductsUnified + ProductsVisaExt 的双向同步
"""

import re
from datetime import datetime
from App_new.exts import db


class VisaSyncService:
    """签证产品与统一产品同步服务"""

    @staticmethod
    def sync_visa_type_to_product(visa_type):
        """
        同步单个签证类型到统一产品系统

        Args:
            visa_type: VisaTypes 对象

        Returns:
            ProductsUnified 对象
        """
        from App_new.business.products.models import ProductsUnified, ProductCategory
        from App_new.business.products.models.products_visa_ext import ProductsVisaExt

        # 查找现有的关联产品
        ext = ProductsVisaExt.query.filter_by(visa_type_id=visa_type.id).first()

        if ext:
            # 更新现有产品
            product = ext.product
        else:
            # 创建新产品
            product_code = ProductsUnified.generate_product_code(ProductCategory.VISA)
            product = ProductsUnified(
                product_code=product_code,
                product_category=ProductCategory.VISA,
                created_at=visa_type.created_at or datetime.utcnow(),
            )
            db.session.add(product)
            db.session.flush()  # 获取 product.id

            # 创建扩展记录
            ext = ProductsVisaExt(
                product_id=product.id,
                visa_type_id=visa_type.id,
            )
            db.session.add(ext)

        # 同步字段
        VisaSyncService._sync_fields(product, ext, visa_type)

        # 更新 ext_table_id
        product.ext_table_id = visa_type.id

        return product

    @staticmethod
    def _sync_fields(product, ext, visa_type):
        """
        同步字段值

        Args:
            product: ProductsUnified 对象
            ext: ProductsVisaExt 对象
            visa_type: VisaTypes 对象
        """
        # 同步到 ProductsUnified
        product.product_name = visa_type.visa_type
        product.product_status = 'active' if visa_type.is_active else 'inactive'
        product.updated_at = visa_type.updated_at or datetime.utcnow()
        product.valid_until = visa_type.valid_until

        # 同步国家信息
        if visa_type.country:
            product.country = visa_type.country.country_name_CN

        # 解析售价
        product.base_price = VisaSyncService._parse_price(visa_type.fee)

        # 解析成本
        product.cost_price = VisaSyncService._parse_price(visa_type.cost)

        # 同步到 ProductsVisaExt
        ext.visa_name = visa_type.visa_type
        ext.processing_time = visa_type.processing_time
        ext.country_id = visa_type.country_id
        ext.important_notes = visa_type.introduction

        if visa_type.country:
            ext.destination_country = visa_type.country.country_name_CN
            ext.destination_country_en = visa_type.country.country_name_EN
            ext.destination_country_code = visa_type.country.country_code

        # 同步费用到扩展表
        ext.total_fee = VisaSyncService._parse_price(visa_type.fee)

    @staticmethod
    def _parse_price(price_str):
        """
        从价格字符串中解析数字

        Args:
            price_str: 价格字符串，如 "$150" 或 "150 SGD"

        Returns:
            float 或 None
        """
        if not price_str:
            return None
        try:
            # 提取数字（包括小数）
            numbers = re.findall(r'[\d.]+', str(price_str))
            if numbers:
                return float(numbers[0])
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def sync_all_visa_types():
        """
        批量同步所有签证类型到统一产品系统

        Returns:
            int: 同步的记录数
        """
        from App_new.business.visa.models.Visamodels import VisaTypes

        visa_types = VisaTypes.query.all()
        synced_count = 0

        for vt in visa_types:
            try:
                VisaSyncService.sync_visa_type_to_product(vt)
                synced_count += 1
            except Exception as e:
                print(f"同步签证类型 {vt.visa_type} 失败: {str(e)}")
                continue

        db.session.commit()
        return synced_count

    @staticmethod
    def delete_product_for_visa_type(visa_type_id):
        """
        删除签证类型时同步删除关联的统一产品

        Args:
            visa_type_id: 签证类型ID
        """
        from App_new.business.products.models.products_visa_ext import ProductsVisaExt

        ext = ProductsVisaExt.query.filter_by(visa_type_id=visa_type_id).first()
        if ext:
            product = ext.product
            db.session.delete(ext)
            if product:
                db.session.delete(product)

    @staticmethod
    def get_product_for_visa_type(visa_type_id):
        """
        获取签证类型关联的统一产品

        Args:
            visa_type_id: 签证类型ID

        Returns:
            ProductsUnified 对象或 None
        """
        from App_new.business.products.models.products_visa_ext import ProductsVisaExt

        ext = ProductsVisaExt.query.filter_by(visa_type_id=visa_type_id).first()
        if ext:
            return ext.product
        return None

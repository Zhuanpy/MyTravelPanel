# -*- coding: utf-8 -*-
"""
产品同步工具
用于将各业务模块的产品同步到统一产品表
"""

from App_new.exts import db
from App_new.business.products.models import (
    ProductsUnified,
    ProductCategory,
    ProductSubCategory,
    ProductsPrice,
    PeopleType,
)


def sync_tour_product_to_unified(tour_product, created_by=None):
    """
    将旅游产品同步到统一产品表

    Args:
        tour_product: 旅游产品对象 (package_products)
        created_by: 创建人

    Returns:
        ProductsUnified: 同步后的统一产品对象
    """
    # 产品类型映射
    product_type_map = {
        '跟团游': ProductSubCategory.TOUR_GROUP,
        '自由行': ProductSubCategory.TOUR_FREE,
        '定制游': ProductSubCategory.TOUR_CUSTOM,
        '当地游': ProductSubCategory.TOUR_LOCAL,
    }

    # 检查是否已存在对应的统一产品
    unified = ProductsUnified.query.filter_by(
        product_category=ProductCategory.TOUR,
        ext_table_id=tour_product.id
    ).first()

    # 获取国家/城市信息
    country = None
    city = None
    if tour_product.city:
        country = tour_product.city.country_name
        city = tour_product.city.city_name
    elif tour_product.city_name:
        city = tour_product.city_name

    # 映射子类别
    sub_category = product_type_map.get(
        tour_product.product_type,
        ProductSubCategory.TOUR_GROUP
    )

    if unified:
        # 更新现有记录（保留原有编号）
        unified.product_name = tour_product.product_name
        unified.product_sub_category = sub_category
        unified.product_status = tour_product.product_status or 'draft'
        unified.is_featured = tour_product.is_featured or False
        unified.supplier_id = tour_product.supplier_id
        unified.country = country
        unified.city = city
        unified.departure_city = tour_product.departure_city
        unified.destination = tour_product.destination_city
        unified.base_price = tour_product.base_price
        unified.currency = tour_product.currency or 'SGD'
        unified.cover_image = tour_product.cover_image
        unified.gallery_images = tour_product.gallery_images
        unified.description = tour_product.product_description
        unified.includes = tour_product.included_services
        unified.excludes = tour_product.excluded_services
        unified.important_notes = tour_product.important_notes
        unified.valid_from = tour_product.valid_from
        unified.valid_until = tour_product.valid_until
        unified.tags = tour_product.tags
        unified.updated_by = created_by
    else:
        # 创建新记录（使用统一编号规则）
        from App_new.shared.models.business_types import generate_product_code
        product_code = generate_product_code('tour')

        unified = ProductsUnified(
            product_code=product_code,
            product_name=tour_product.product_name,
            product_category=ProductCategory.TOUR,
            product_sub_category=sub_category,
            sale_type='service',
            product_status=tour_product.product_status or 'draft',
            is_featured=tour_product.is_featured or False,
            is_hot=False,
            is_new=True,  # 新产品标记
            supplier_id=tour_product.supplier_id,
            country=country,
            city=city,
            departure_city=tour_product.departure_city,
            destination=tour_product.destination_city,
            base_price=tour_product.base_price,
            currency=tour_product.currency or 'SGD',
            cover_image=tour_product.cover_image,
            gallery_images=tour_product.gallery_images,
            description=tour_product.product_description,
            includes=tour_product.included_services,
            excludes=tour_product.excluded_services,
            important_notes=tour_product.important_notes,
            valid_from=tour_product.valid_from,
            valid_until=tour_product.valid_until,
            tags=tour_product.tags,
            ext_table_id=tour_product.id,
            created_by=created_by,
        )
        db.session.add(unified)

    db.session.flush()  # 获取ID

    # 同步价格信息
    _sync_tour_prices(unified, tour_product)

    return unified


def _sync_tour_prices(unified, tour_product):
    """同步旅游产品价格"""
    currency = tour_product.currency or 'SGD'

    # 获取或创建成人价
    if tour_product.base_price:
        adult_price = ProductsPrice.query.filter_by(
            product_id=unified.id,
            people_type=PeopleType.ADULT,
            price_type='standard'
        ).first()

        if adult_price:
            adult_price.selling_price = tour_product.base_price
            adult_price.currency = currency
        else:
            adult_price = ProductsPrice(
                product_id=unified.id,
                price_type='standard',
                price_name='成人价',
                people_type=PeopleType.ADULT,
                selling_price=tour_product.base_price,
                currency=currency,
                is_active=True,
            )
            db.session.add(adult_price)

    # 获取或创建儿童价
    if tour_product.child_price:
        child_price = ProductsPrice.query.filter_by(
            product_id=unified.id,
            people_type=PeopleType.CHILD,
            price_type='standard'
        ).first()

        if child_price:
            child_price.selling_price = tour_product.child_price
            child_price.currency = currency
        else:
            child_price = ProductsPrice(
                product_id=unified.id,
                price_type='standard',
                price_name='儿童价',
                people_type=PeopleType.CHILD,
                selling_price=tour_product.child_price,
                currency=currency,
                is_active=True,
            )
            db.session.add(child_price)

    # 获取或创建婴儿价
    if tour_product.infant_price:
        infant_price = ProductsPrice.query.filter_by(
            product_id=unified.id,
            people_type=PeopleType.INFANT,
            price_type='standard'
        ).first()

        if infant_price:
            infant_price.selling_price = tour_product.infant_price
            infant_price.currency = currency
        else:
            infant_price = ProductsPrice(
                product_id=unified.id,
                price_type='standard',
                price_name='婴儿价',
                people_type=PeopleType.INFANT,
                selling_price=tour_product.infant_price,
                currency=currency,
                is_active=True,
            )
            db.session.add(infant_price)


def delete_unified_product_by_tour(tour_product_id):
    """
    删除旅游产品对应的统一产品记录

    Args:
        tour_product_id: 旅游产品ID
    """
    unified = ProductsUnified.query.filter_by(
        product_category=ProductCategory.TOUR,
        ext_table_id=tour_product_id
    ).first()

    if unified:
        # 删除关联的价格记录
        ProductsPrice.query.filter_by(product_id=unified.id).delete()
        # 删除统一产品记录
        db.session.delete(unified)


def sync_visa_type_to_unified(visa_type, created_by=None):
    """
    将签证类型同步到统一产品表

    Args:
        visa_type: 签证类型对象 (visa_types)
        created_by: 创建人

    Returns:
        ProductsUnified: 同步后的统一产品对象
    """
    import re

    def parse_fee(fee_str):
        """解析费用字符串"""
        if not fee_str:
            return None
        try:
            numbers = re.findall(r'[\d.]+', str(fee_str))
            if numbers:
                return float(numbers[0])
        except (ValueError, TypeError):
            pass
        return None

    # 检查是否已存在对应的统一产品
    unified = ProductsUnified.query.filter_by(
        product_category=ProductCategory.VISA,
        ext_table_id=visa_type.id
    ).first()

    # 获取国家信息
    country = visa_type.country
    country_name = country.country_name_CN if country else '未知'
    country_code = country.country_code if country else None

    # 生成产品名称
    product_name = f"{country_name}{visa_type.visa_type}"

    # 解析费用
    total_fee = parse_fee(visa_type.fee)

    if unified:
        # 更新现有记录
        unified.product_name = product_name
        unified.product_short_name = visa_type.visa_type
        unified.product_status = 'active' if visa_type.is_active else 'inactive'
        unified.country = country_name
        unified.base_price = total_fee
        unified.description = visa_type.introduction
        unified.valid_until = visa_type.valid_until.date() if visa_type.valid_until else None
        unified.updated_by = created_by
    else:
        # 创建新记录
        product_code = f"VISA-{country_code or 'XX'}-{visa_type.id:04d}"

        unified = ProductsUnified(
            product_code=product_code,
            product_name=product_name,
            product_short_name=visa_type.visa_type,
            product_category=ProductCategory.VISA,
            product_sub_category='tourist_visa',  # 默认旅游签证
            sale_type='service',
            product_status='active' if visa_type.is_active else 'inactive',
            country=country_name,
            base_price=total_fee,
            currency='SGD',
            description=visa_type.introduction,
            valid_until=visa_type.valid_until.date() if visa_type.valid_until else None,
            ext_table_id=visa_type.id,
            created_by=created_by,
        )
        db.session.add(unified)

    return unified

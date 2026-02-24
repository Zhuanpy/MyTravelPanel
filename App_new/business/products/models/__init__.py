# -*- coding: utf-8 -*-
"""
统一产品模型
"""

from .products_unified import (
    ProductsUnified,
    ProductCategory,
    ProductSubCategory
)
from .products_price import (
    ProductsPrice,
    PriceType,
    PeopleType
)
from .products_rule import (
    ProductsRule,
    RuleType
)
from .products_ticket_ext import (
    ProductsTicketExt,
    TicketType,
    TicketDelivery
)
from .products_ticket_variant import ProductsTicketVariant
from .products_car_ext import (
    ProductsCarExt,
    CarServiceType,
    VehicleType
)
from .products_cruise_ext import (
    ProductsCruiseExt,
    CabinType
)
from .products_hotel_ext import (
    ProductsHotelExt,
    HotelStarRating,
    RoomType,
    BedType
)
from .products_insurance_ext import (
    ProductsInsuranceExt,
    InsuranceType,
    CoverageRegion
)
from .products_visa_ext import (
    ProductsVisaExt,
    VisaCategory,
    VisaEntryType
)

__all__ = [
    # 主表
    'ProductsUnified',
    'ProductCategory',
    'ProductSubCategory',
    # 价格表
    'ProductsPrice',
    'PriceType',
    'PeopleType',
    # 规则表
    'ProductsRule',
    'RuleType',
    # 门票扩展
    'ProductsTicketExt',
    'TicketType',
    'TicketDelivery',
    # 门票变体
    'ProductsTicketVariant',
    # 用车扩展
    'ProductsCarExt',
    'CarServiceType',
    'VehicleType',
    # 邮轮扩展
    'ProductsCruiseExt',
    'CabinType',
    # 酒店扩展
    'ProductsHotelExt',
    'HotelStarRating',
    'RoomType',
    'BedType',
    # 保险扩展
    'ProductsInsuranceExt',
    'InsuranceType',
    'CoverageRegion',
    # 签证扩展
    'ProductsVisaExt',
    'VisaCategory',
    'VisaEntryType',
]

# -*- coding: utf-8 -*-
"""
通用访问统计服务
"""

import uuid
from flask import request
from App_new.exts import db
from App_new.shared.models.visit_stats import ProductVisitStats

class VisitStatsService:
    """访问统计服务类"""
    
    PRODUCT_TYPES = {
        'visa': '签证',
        'tour': '旅游',
        'flight': '机票',
        'hotel': '酒店',
        'package': '套餐'
    }
    
    @staticmethod
    def get_visitor_info():
        """获取访问者信息"""
        return {
            'visitor_ip': request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR')),
            'user_agent': request.headers.get('User-Agent'),
            'referer': request.headers.get('Referer'),
            'session_id': str(uuid.uuid4())
        }
    
    @staticmethod
    def record_product_visit(product_type, product_id, product_name, product_category=None, additional_data=None):
        """记录产品访问"""
        try:
            print(f"开始记录产品访问: {product_type}, {product_id}, {product_name}")
            visitor_info = VisitStatsService.get_visitor_info()
            print(f"访问者信息: {visitor_info}")
            
            result = ProductVisitStats.record_visit(
                product_type=product_type,
                product_id=product_id,
                product_name=product_name,
                product_category=product_category,
                visitor_ip=visitor_info['visitor_ip'],
                user_agent=visitor_info['user_agent'],
                referer=visitor_info['referer'],
                session_id=visitor_info['session_id'],
                additional_data=additional_data
            )
            print(f"记录结果: {result}")
            return result
        except Exception as e:
            print(f"记录产品访问失败: {str(e)}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def record_visa_visit(visa_type_id, visa_type_name, country_name=None):
        """记录签证访问"""
        return VisitStatsService.record_product_visit(
            product_type='visa',
            product_id=visa_type_id,
            product_name=visa_type_name,
            product_category=country_name
        )
    
    @staticmethod
    def record_tour_visit(tour_id, tour_name, destination=None):
        """记录旅游产品访问"""
        return VisitStatsService.record_product_visit(
            product_type='tour',
            product_id=tour_id,
            product_name=tour_name,
            product_category=destination
        )
    
    @staticmethod
    def record_flight_visit(flight_id, flight_name, route=None):
        """记录机票访问"""
        return VisitStatsService.record_product_visit(
            product_type='flight',
            product_id=flight_id,
            product_name=flight_name,
            product_category=route
        )
    
    @staticmethod
    def get_product_stats(product_type=None, days=30):
        """获取产品统计"""
        return ProductVisitStats.get_visit_stats(product_type=product_type, days=days)
    
    @staticmethod
    def get_popular_products(product_type=None, limit=10, days=30):
        """获取热门产品"""
        return ProductVisitStats.get_popular_products(product_type=product_type, limit=limit, days=days)
    
    @staticmethod
    def get_overall_stats(days=30):
        """获取整体统计"""
        return ProductVisitStats.get_stats_summary(days=days)

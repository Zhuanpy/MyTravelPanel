# -*- coding: utf-8 -*-
"""
通用产品访问统计模型
"""

from datetime import datetime
from App_new.exts import db

class ProductVisitStats(db.Model):
    """通用产品访问统计模型"""
    __tablename__ = 'product_visit_stats'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_type = db.Column(db.String(50), nullable=False)  # visa, tour, flight, hotel等
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    product_category = db.Column(db.String(100), nullable=True)
    visitor_ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    referer = db.Column(db.Text, nullable=True)
    visit_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    session_id = db.Column(db.String(100), nullable=True)
    additional_data = db.Column(db.Text, nullable=True)  # JSON格式的额外数据
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ProductVisitStats(id={self.id}, type='{self.product_type}', product='{self.product_name}', time='{self.visit_time}')>"

    @staticmethod
    def record_visit(product_type, product_id, product_name, product_category=None, 
                    visitor_ip=None, user_agent=None, referer=None, session_id=None, 
                    additional_data=None):
        """记录产品访问统计"""
        try:
            import json
            
            print(f"准备创建访问记录: {product_type}, {product_id}, {product_name}")
            
            visit_record = ProductVisitStats(
                product_type=product_type,
                product_id=product_id,
                product_name=product_name,
                product_category=product_category,
                visitor_ip=visitor_ip,
                user_agent=user_agent,
                referer=referer,
                session_id=session_id,
                additional_data=json.dumps(additional_data) if additional_data else None
            )
            
            print(f"访问记录对象创建成功: {visit_record}")
            
            db.session.add(visit_record)
            print("已添加到数据库会话")
            
            db.session.commit()
            print("数据库提交成功")
            
            return True
        except Exception as e:
            db.session.rollback()
            print(f"记录访问统计失败: {str(e)}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            return False

    @staticmethod
    def get_visit_stats(product_type=None, product_id=None, days=30):
        """获取访问统计"""
        try:
            query = ProductVisitStats.query
            if product_type:
                query = query.filter_by(product_type=product_type)
            if product_id:
                query = query.filter_by(product_id=product_id)
            
            # 按时间过滤
            from datetime import datetime, timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(ProductVisitStats.visit_time >= start_date)
            
            return query.order_by(ProductVisitStats.visit_time.desc()).all()
        except Exception as e:
            print(f"获取访问统计失败: {str(e)}")
            return []

    @staticmethod
    def get_popular_products(product_type=None, limit=10, days=30):
        """获取热门产品"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = db.session.query(
                ProductVisitStats.product_type,
                ProductVisitStats.product_id,
                ProductVisitStats.product_name,
                ProductVisitStats.product_category,
                func.count(ProductVisitStats.id).label('visit_count')
            ).filter(
                ProductVisitStats.visit_time >= start_date
            )
            
            if product_type:
                query = query.filter_by(product_type=product_type)
            
            popular_products = query.group_by(
                ProductVisitStats.product_type,
                ProductVisitStats.product_id,
                ProductVisitStats.product_name,
                ProductVisitStats.product_category
            ).order_by(
                func.count(ProductVisitStats.id).desc()
            ).limit(limit).all()
            
            return popular_products
        except Exception as e:
            print(f"获取热门产品失败: {str(e)}")
            return []

    @staticmethod
    def get_stats_summary(days=30):
        """获取统计概览"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 总访问次数
            total_visits = ProductVisitStats.query.filter(
                ProductVisitStats.visit_time >= start_date
            ).count()
            
            # 独立访客数
            unique_visitors = db.session.query(
                func.count(func.distinct(ProductVisitStats.session_id))
            ).filter(
                ProductVisitStats.visit_time >= start_date
            ).scalar() or 0
            
            # 按产品类型分组统计
            stats_by_type = db.session.query(
                ProductVisitStats.product_type,
                func.count(ProductVisitStats.id).label('visit_count')
            ).filter(
                ProductVisitStats.visit_time >= start_date
            ).group_by(
                ProductVisitStats.product_type
            ).all()
            
            return {
                'total_visits': total_visits,
                'unique_visitors': unique_visitors,
                'stats_by_type': dict(stats_by_type)
            }
        except Exception as e:
            print(f"获取统计概览失败: {str(e)}")
            return {
                'total_visits': 0,
                'unique_visitors': 0,
                'stats_by_type': {}
            }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试访问统计功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from App_new import create_app
from App_new.shared.services.visit_stats_service import VisitStatsService
from App_new.shared.models.visit_stats import ProductVisitStats

def test_visit_stats():
    """测试访问统计功能"""
    app = create_app()
    
    with app.app_context():
        try:
            # 测试记录访问
            print("测试记录访问统计...")
            result = VisitStatsService.record_visa_visit(
                visa_type_id=1,
                visa_type_name="日本多次签证",
                country_name="日本"
            )
            
            if result:
                print("✅ 访问记录成功")
                
                # 查询访问统计
                stats = VisitStatsService.get_product_stats(product_type='visa', days=30)
                print(f"✅ 查询到 {len(stats)} 条访问记录")
                
                # 获取热门产品
                popular = VisitStatsService.get_popular_products(product_type='visa', limit=5, days=30)
                print(f"✅ 查询到 {len(popular)} 个热门产品")
                
                # 获取整体统计
                summary = VisitStatsService.get_overall_stats(days=30)
                print(f"✅ 整体统计: 总访问 {summary['total_visits']} 次, 独立访客 {summary['unique_visitors']} 人")
                
            else:
                print("❌ 访问记录失败")
                
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_visit_stats()

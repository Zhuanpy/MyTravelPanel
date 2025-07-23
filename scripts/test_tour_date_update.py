#!/usr/bin/env python3
"""
测试旅游项目日期更新功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.TourProject import TourGroup, TourItinerary
from datetime import datetime, timedelta

def test_tour_date_update():
    """测试旅游项目日期更新功能"""
    app = create_app()
    
    with app.app_context():
        try:
            print("测试旅游项目日期更新功能...")
            
            # 查找一个测试团队
            test_group = TourGroup.query.first()
            if not test_group:
                print("❌ 没有找到测试团队")
                return
            
            print(f"找到测试团队: ID={test_group.id}, 名称={test_group.title}")
            print(f"当前出发日期: {test_group.departure_date}")
            print(f"当前返回日期: {test_group.return_date}")
            
            # 获取该团队的行程安排
            itineraries = TourItinerary.query.filter_by(tour_id=test_group.id).order_by(TourItinerary.date.asc()).all()
            print(f"当前行程安排数量: {len(itineraries)}")
            
            if itineraries:
                print("当前行程安排:")
                for i, itinerary in enumerate(itineraries):
                    print(f"  {i+1}. {itinerary.day_title} - {itinerary.date}")
            
            # 模拟日期更新
            print(f"\n模拟日期更新...")
            old_departure_date = test_group.departure_date
            old_return_date = test_group.return_date
            
            # 将出发日期和返回日期都推迟3天
            new_departure_date = old_departure_date + timedelta(days=3)
            new_return_date = old_return_date + timedelta(days=3)
            
            print(f"新出发日期: {new_departure_date}")
            print(f"新返回日期: {new_return_date}")
            
            # 更新团队日期
            test_group.departure_date = new_departure_date
            test_group.return_date = new_return_date
            
            # 更新行程安排中的日期
            if itineraries:
                print(f"\n开始更新行程安排日期...")
                for i, itinerary in enumerate(itineraries):
                    # 计算新日期：新出发日期 + 天数差
                    new_date = new_departure_date + timedelta(days=i)
                    
                    # 确保新日期不超过返回日期
                    if new_date <= new_return_date:
                        old_date = itinerary.date
                        itinerary.date = new_date
                        print(f"更新行程 {itinerary.day_title}: {old_date} -> {new_date}")
                    else:
                        print(f"警告：行程 {itinerary.day_title} 的新日期 {new_date} 超过返回日期 {new_return_date}")
            
            # 保存更改
            db.session.commit()
            print(f"\n✅ 日期更新完成")
            
            # 验证更新结果
            print(f"\n验证更新结果:")
            updated_group = TourGroup.query.get(test_group.id)
            print(f"团队出发日期: {updated_group.departure_date}")
            print(f"团队返回日期: {updated_group.return_date}")
            
            updated_itineraries = TourItinerary.query.filter_by(tour_id=test_group.id).order_by(TourItinerary.date.asc()).all()
            print(f"更新后的行程安排:")
            for i, itinerary in enumerate(updated_itineraries):
                print(f"  {i+1}. {itinerary.day_title} - {itinerary.date}")
            
            # 恢复原始日期（可选）
            print(f"\n是否要恢复原始日期？(y/n): ", end="")
            # 这里可以添加用户输入逻辑，暂时跳过
            
            print("\n✅ 测试完成")
                
        except Exception as e:
            db.session.rollback()
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_tour_date_update() 
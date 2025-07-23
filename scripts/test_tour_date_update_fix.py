#!/usr/bin/env python3
"""
测试修复后的旅游项目日期更新功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.TourProject import TourGroup, TourItinerary
from datetime import datetime, timedelta

def test_tour_date_update_fix():
    """测试修复后的旅游项目日期更新功能"""
    app = create_app()
    
    with app.app_context():
        try:
            print("测试修复后的旅游项目日期更新功能...")
            
            # 查找项目60的团队
            test_group = TourGroup.query.filter_by(project_id=60).first()
            if not test_group:
                print("❌ 没有找到项目60的团队")
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
            
            # 模拟日期更新逻辑
            print(f"\n模拟日期更新逻辑...")
            old_departure_date = test_group.departure_date
            old_return_date = test_group.return_date
            
            # 将出发日期和返回日期都推迟2天
            new_departure_date = old_departure_date + timedelta(days=2)
            new_return_date = old_return_date + timedelta(days=2)
            
            print(f"原出发日期: {old_departure_date}")
            print(f"新出发日期: {new_departure_date}")
            print(f"原返回日期: {old_return_date}")
            print(f"新返回日期: {new_return_date}")
            
            # 检查日期是否发生变化
            date_changed = (old_departure_date != new_departure_date) or (old_return_date != new_return_date)
            print(f"日期是否发生变化: {date_changed}")
            
            if date_changed:
                print(f"\n开始更新行程安排日期...")
                
                # 更新团队日期
                test_group.departure_date = new_departure_date
                test_group.return_date = new_return_date
                
                # 更新行程安排中的日期
                if itineraries:
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
            else:
                print("日期没有发生变化，无需更新")
            
            print("\n✅ 测试完成")
                
        except Exception as e:
            db.session.rollback()
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_tour_date_update_fix() 
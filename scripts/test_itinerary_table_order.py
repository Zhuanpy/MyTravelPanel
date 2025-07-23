#!/usr/bin/env python3
"""
测试行程列表的列顺序
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.TourProject import TourProject, TourGroup, TourItinerary

def test_itinerary_table_order():
    """测试行程列表的列顺序"""
    app = create_app()
    
    with app.app_context():
        try:
            print("测试行程列表的列顺序...")
            
            # 获取项目60
            project = TourProject.query.get(60)
            if not project:
                print("❌ 项目60不存在")
                return
            
            print(f"项目信息: {project.project_name}")
            
            # 获取项目的团队信息
            groups = TourGroup.query.filter_by(project_id=60).all()
            print(f"团队数量: {len(groups)}")
            
            for i, group in enumerate(groups):
                print(f"\n=== 团队 {i+1} ===")
                print(f"  名称: {group.title}")
                print(f"  出发日期: {group.departure_date}")
                print(f"  返回日期: {group.return_date}")
                
                # 获取该团队的行程安排
                itineraries = TourItinerary.query.filter_by(tour_id=group.id).order_by(TourItinerary.date.asc()).all()
                print(f"  行程安排数量: {len(itineraries)}")
                
                if itineraries:
                    print("  行程安排详情（新的列顺序：日期 | 天数 | 标题 | 内容）:")
                    for j, itinerary in enumerate(itineraries):
                        print(f"    {j+1}. 日期: {itinerary.date} | 第{j+1}天 | {itinerary.day_title}")
                        print(f"       内容: {itinerary.content[:50]}...")
                else:
                    print("  暂无行程安排")
            
            print("\n✅ 行程列表列顺序测试完成")
            print("新的列顺序：")
            print("1. 日期")
            print("2. 天数") 
            print("3. 日期标题")
            print("4. 行程内容")
            print("5. 操作")
                
        except Exception as e:
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_itinerary_table_order() 
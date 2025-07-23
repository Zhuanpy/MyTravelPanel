#!/usr/bin/env python3
"""
检查项目60的具体数据，包括团队和行程信息
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.TourProject import TourProject, TourGroup, TourItinerary

def check_project_60_data():
    """检查项目60的具体数据"""
    app = create_app()
    
    with app.app_context():
        try:
            print("检查项目60的数据...")
            
            # 获取项目60
            project = TourProject.query.get(60)
            if not project:
                print("❌ 项目60不存在")
                return
            
            print(f"项目信息:")
            print(f"  ID: {project.id}")
            print(f"  名称: {project.project_name}")
            print(f"  HID: {project.project_hid}")
            print(f"  状态: {project.project_status}")
            print(f"  联系人: {project.contact_person}")
            print(f"  联系方式: {project.contact_info}")
            
            # 获取项目的团队信息
            groups = TourGroup.query.filter_by(project_id=60).all()
            print(f"\n团队数量: {len(groups)}")
            
            for i, group in enumerate(groups):
                print(f"\n=== 团队 {i+1} ===")
                print(f"  ID: {group.id}")
                print(f"  名称: {group.title}")
                print(f"  出发日期: {group.departure_date}")
                print(f"  返回日期: {group.return_date}")
                print(f"  人数: {group.pax}")
                print(f"  旅行社: {group.agency}")
                print(f"  地接社: {group.operator}")
                print(f"  团状态: {group.group_status}")
                
                # 获取该团队的行程安排
                itineraries = TourItinerary.query.filter_by(tour_id=group.id).order_by(TourItinerary.date.asc()).all()
                print(f"  行程安排数量: {len(itineraries)}")
                
                if itineraries:
                    print("  行程安排详情:")
                    for j, itinerary in enumerate(itineraries):
                        print(f"    {j+1}. {itinerary.day_title}")
                        print(f"       日期: {itinerary.date}")
                        print(f"       内容: {itinerary.content[:50]}...")
                        print(f"       创建时间: {itinerary.created_at}")
                        print(f"       更新时间: {itinerary.updated_at}")
                else:
                    print("  暂无行程安排")
            
            print("\n✅ 项目60数据检查完成")
                
        except Exception as e:
            print(f"检查过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    check_project_60_data() 
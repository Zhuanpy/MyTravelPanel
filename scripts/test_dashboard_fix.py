#!/usr/bin/env python3
"""
测试仪表板修复
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.projects.BookingProject import ProjectHeader, ProjectRef, CustomerCompany

def test_dashboard_data():
    """测试仪表板数据获取"""
    app = create_app()
    
    with app.app_context():
        try:
            # 测试获取项目数据
            print("🧪 测试项目数据获取...")
            
            # 获取最近的项目（最近10个）
            recent_projects_query = ProjectHeader.query.order_by(ProjectHeader.created_at.desc()).limit(10)
            projects = []
            
            for project in recent_projects_query:
                print(f"处理项目: {project.hid}")
                
                # 计算项目财务数据
                refs = ProjectRef.query.filter_by(header_id=project.id).all()
                total_selling_price = sum([float(ref.selling_price or 0) for ref in refs])
                total_cost_price = sum([float(ref.cost_price or 0) for ref in refs])
                total_profit = total_selling_price - total_cost_price
                
                # 获取客户公司名称
                client_name = '未指定客户'
                if project.company_id and project.company:
                    client_name = project.company.company_name
                    print(f"  客户: {client_name}")
                else:
                    print(f"  客户: {client_name} (无关联公司)")
                
                # 简化项目数据
                project_data = {
                    'id': project.id,
                    'hid': project.hid,
                    'name': project.desc or f'项目 {project.hid}',
                    'client': client_name,
                    'leader': project.leader_name or '未指定负责人',
                    'contact': project.contact or '未指定联系人',
                    'status': project.status,
                    'type': project.type or '综合',
                    'created_at': project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else '',
                    'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M') if project.updated_at else '',
                    'total_selling': total_selling_price,
                    'total_cost': total_cost_price,
                    'total_profit': total_profit,
                    'ref_count': len(refs)
                }
                projects.append(project_data)
                print(f"  状态: {project.status}, REF数量: {len(refs)}")
            
            print(f"\n✅ 成功获取 {len(projects)} 个项目数据")
            
            # 测试统计数据
            print("\n🧪 测试统计数据...")
            total_projects = ProjectHeader.query.count()
            active_projects = ProjectHeader.query.filter_by(status='active').count()
            print(f"总项目数: {total_projects}")
            print(f"活跃项目数: {active_projects}")
            
            print("\n🎉 仪表板数据获取测试通过！")
            return True
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            import traceback
            print(f"错误详情: {traceback.format_exc()}")
            return False

if __name__ == "__main__":
    print("开始测试仪表板数据获取...")
    success = test_dashboard_data()
    if success:
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 测试失败，需要进一步检查") 
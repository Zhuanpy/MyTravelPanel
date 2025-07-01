import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.Visamodels import VisaProject, VisaTypes

def check_visa_project(project_id):
    """检查签证项目是否存在"""
    app = create_app()
    with app.app_context():
        # 检查项目是否存在
        project = VisaProject.query.get(project_id)
        if project:
            print(f"✓ 项目ID {project_id} 存在")
            print(f"  项目名称: {project.project_folder_name}")
            print(f"  签证类型: {project.visa_type}")
            print(f"  申请人: {project.applicant_name}")
            print(f"  状态: {project.visa_status}")
            print(f"  创建日期: {project.created_date}")
            
            # 检查签证类型是否存在
            if project.visa_type:
                visa_type = VisaTypes.query.filter_by(visa_type=project.visa_type).first()
                if visa_type:
                    print(f"✓ 签证类型 '{project.visa_type}' 存在")
                else:
                    print(f"✗ 签证类型 '{project.visa_type}' 不存在")
            else:
                print("⚠ 项目没有签证类型")
        else:
            print(f"✗ 项目ID {project_id} 不存在")
            
            # 显示所有项目ID
            all_projects = VisaProject.query.all()
            print(f"\n当前数据库中的所有项目:")
            for p in all_projects:
                print(f"  ID: {p.id}, 名称: {p.project_folder_name}, 类型: {p.visa_type}")

if __name__ == "__main__":
    check_visa_project(291) 
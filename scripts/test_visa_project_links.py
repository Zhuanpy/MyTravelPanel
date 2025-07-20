#!/usr/bin/env python3
"""
测试签证项目HID和REF创建功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.Product.Visamodels import VisaProject, VisaTypes
from App.models.projects.BookingProject import ProjectHeader, ProjectRef
from App.models.Product.BusinessType import BusinessType

def test_visa_project_links():
    """测试签证项目HID和REF创建功能"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始测试签证项目HID和REF创建功能...")
            
            # 1. 检查签证业务类型
            print("\n=== 检查签证业务类型 ===")
            visa_business_type = BusinessType.query.filter_by(code='visa').first()
            if visa_business_type:
                print(f"签证业务类型: ID={visa_business_type.id}, 名称={visa_business_type.name}, 代码={visa_business_type.code}")
            else:
                print("❌ 未找到签证业务类型")
                return
            
            # 2. 检查签证项目
            print("\n=== 检查签证项目 ===")
            visa_projects = VisaProject.query.limit(5).all()
            print(f"找到 {len(visa_projects)} 个签证项目")
            
            for i, project in enumerate(visa_projects, 1):
                print(f"\n项目 {i}:")
                print(f"  ID: {project.id}")
                print(f"  申请人: {project.applicant_name}")
                print(f"  签证类型: {project.visa_type}")
                print(f"  联系人: {project.contact_name}")
                print(f"  当前HID关联: {project.header_id}")
                print(f"  当前REF关联: {project.ref_id}")
                
                # 检查是否已有关联
                if project.header_id:
                    header = ProjectHeader.query.get(project.header_id)
                    print(f"  关联的HID: {header.hid if header else '未找到'}")
                
                if project.ref_id:
                    ref = ProjectRef.query.get(project.ref_id)
                    print(f"  关联的REF: {ref.ref_number if ref else '未找到'}")
            
            # 3. 测试创建HID和REF的逻辑
            print("\n=== 测试创建逻辑 ===")
            
            # 选择一个没有关联的项目进行测试
            test_project = None
            for project in visa_projects:
                if not project.header_id and not project.ref_id:
                    test_project = project
                    break
            
            if test_project:
                print(f"选择测试项目: ID={test_project.id}, 申请人={test_project.applicant_name}")
                
                # 获取签证类型信息
                types_info = VisaTypes.query.filter_by(visa_type=test_project.visa_type).first()
                if types_info:
                    print(f"签证类型信息: {types_info.visa_type}, 国家: {types_info.country.country_name_CN if types_info.country else '未知'}")
                
                # 模拟创建HID
                hid = ProjectHeader.generate_hid()
                print(f"生成的HID: {hid}")
                
                # 模拟创建REF
                ref_number = ProjectRef.generate_ref_number(hid)
                print(f"生成的REF: {ref_number}")
                
                print("✅ 创建逻辑测试通过")
            else:
                print("⚠️ 没有找到合适的测试项目（所有项目都已关联）")
            
            # 4. 检查现有的HID和REF
            print("\n=== 检查现有的HID和REF ===")
            
            # 检查已关联的项目
            linked_projects = VisaProject.query.filter(
                (VisaProject.header_id.isnot(None)) | (VisaProject.ref_id.isnot(None))
            ).all()
            
            print(f"已关联HID或REF的项目数: {len(linked_projects)}")
            
            for project in linked_projects:
                print(f"\n项目 {project.id} ({project.applicant_name}):")
                if project.header_id:
                    header = ProjectHeader.query.get(project.header_id)
                    print(f"  HID: {header.hid if header else '未找到'}")
                if project.ref_id:
                    ref = ProjectRef.query.get(project.ref_id)
                    print(f"  REF: {ref.ref_number if ref else '未找到'}")
            
            print("\n签证项目HID和REF创建功能测试完成！")
                
        except Exception as e:
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_visa_project_links() 
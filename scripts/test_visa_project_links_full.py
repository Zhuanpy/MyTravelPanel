#!/usr/bin/env python3
"""
完整测试签证项目HID和REF创建功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.Product.Visamodels import VisaProject, VisaTypes
from App.models.projects.BookingProject import ProjectHeader, ProjectRef
from App.models.Product.BusinessType import BusinessType

def test_visa_project_links_full():
    """完整测试签证项目HID和REF创建功能"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始完整测试签证项目HID和REF创建功能...")
            
            # 1. 选择一个测试项目
            print("\n=== 选择测试项目 ===")
            test_project = VisaProject.query.filter(
                VisaProject.header_id.is_(None),
                VisaProject.ref_id.is_(None)
            ).first()
            
            if not test_project:
                print("❌ 没有找到合适的测试项目（所有项目都已关联）")
                return
            
            print(f"选择测试项目: ID={test_project.id}")
            print(f"  申请人: {test_project.applicant_name}")
            print(f"  签证类型: {test_project.visa_type}")
            print(f"  联系人: {test_project.contact_name}")
            print(f"  当前HID关联: {test_project.header_id}")
            print(f"  当前REF关联: {test_project.ref_id}")
            
            # 2. 获取签证类型信息
            print("\n=== 获取签证类型信息 ===")
            types_info = VisaTypes.query.filter_by(visa_type=test_project.visa_type).first()
            if types_info:
                print(f"签证类型: {types_info.visa_type}")
                print(f"国家: {types_info.country.country_name_CN if types_info.country else '未知'}")
            else:
                print("❌ 未找到签证类型信息")
                return
            
            # 3. 获取签证业务类型
            print("\n=== 获取签证业务类型 ===")
            visa_business_type = BusinessType.query.filter_by(code='visa').first()
            if visa_business_type:
                print(f"签证业务类型: ID={visa_business_type.id}, 名称={visa_business_type.name}")
            else:
                print("❌ 未找到签证业务类型")
                return
            
            # 4. 创建HID
            print("\n=== 创建HID ===")
            hid = ProjectHeader.generate_hid()
            print(f"生成的HID: {hid}")
            
            header = ProjectHeader(
                hid=hid,
                desc=f"{test_project.applicant_name} {test_project.visa_type}签证项目",
                contact=test_project.contact_name or test_project.applicant_name,
                currency='SGD',
                type='visa',
                source='visa_system',
                country=types_info.country.country_name_CN if types_info.country else '未知',
                status='active'
            )
            db.session.add(header)
            db.session.flush()
            print(f"✅ HID创建成功: ID={header.id}, HID={header.hid}")
            
            # 5. 创建REF
            print("\n=== 创建REF ===")
            ref_number = ProjectRef.generate_ref_number(header.hid)
            print(f"生成的REF: {ref_number}")
            
            ref = ProjectRef(
                header_id=header.id,
                ref_number=ref_number,
                name=f"{test_project.applicant_name} {test_project.visa_type}签证",
                ref_type_id=visa_business_type.id,
                description=f"{test_project.applicant_name}的{test_project.visa_type}签证申请",
                contact_name=test_project.contact_name or test_project.applicant_name,
                expected_delivery_date=test_project.estimated_date,
                remarks=test_project.remarks,
                status='processing',
                payment_status='unpaid'
            )
            db.session.add(ref)
            db.session.flush()
            print(f"✅ REF创建成功: ID={ref.id}, REF={ref.ref_number}")
            
            # 6. 更新签证项目关联
            print("\n=== 更新签证项目关联 ===")
            test_project.header_id = header.id
            test_project.ref_id = ref.id
            db.session.commit()
            print(f"✅ 签证项目关联更新成功")
            
            # 7. 验证关联结果
            print("\n=== 验证关联结果 ===")
            # 重新查询项目
            updated_project = VisaProject.query.get(test_project.id)
            print(f"项目ID: {updated_project.id}")
            print(f"HID关联: {updated_project.header_id}")
            print(f"REF关联: {updated_project.ref_id}")
            
            if updated_project.header:
                print(f"关联的HID: {updated_project.header.hid}")
            if updated_project.ref:
                print(f"关联的REF: {updated_project.ref.ref_number}")
            
            # 8. 验证项目主表和REF明细
            print("\n=== 验证项目主表和REF明细 ===")
            header_verify = ProjectHeader.query.get(header.id)
            ref_verify = ProjectRef.query.get(ref.id)
            
            print(f"项目主表验证:")
            print(f"  HID: {header_verify.hid}")
            print(f"  描述: {header_verify.desc}")
            print(f"  联系人: {header_verify.contact}")
            print(f"  状态: {header_verify.status}")
            
            print(f"REF明细验证:")
            print(f"  REF编号: {ref_verify.ref_number}")
            print(f"  名称: {ref_verify.name}")
            print(f"  描述: {ref_verify.description}")
            print(f"  状态: {ref_verify.status}")
            print(f"  支付状态: {ref_verify.payment_status}")
            
            print("\n✅ 签证项目HID和REF创建功能测试完成！")
            print(f"测试项目ID: {test_project.id}")
            print(f"创建的HID: {header.hid}")
            print(f"创建的REF: {ref.ref_number}")
                
        except Exception as e:
            db.session.rollback()
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_visa_project_links_full() 
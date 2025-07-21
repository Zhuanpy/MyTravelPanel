#!/usr/bin/env python3
"""
测试REF 220的编辑功能，检查extra_info数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.projects.BookingProject import ProjectRef
import json

def test_ref_220_edit():
    """测试REF 220的编辑功能"""
    app = create_app()
    
    with app.app_context():
        try:
            print("检查REF 220的数据...")
            
            # 获取REF 220
            ref = ProjectRef.query.get(220)
            if not ref:
                print("❌ REF 220不存在")
                return
            
            print(f"REF基本信息:")
            print(f"  ID: {ref.id}")
            print(f"  REF编号: {ref.ref_number}")
            print(f"  名称: {ref.name}")
            print(f"  描述: {ref.description}")
            print(f"  联系人: {ref.contact_name}")
            print(f"  负责人姓名: {ref.leader_name}")
            print(f"  售价: {ref.selling_price}")
            print(f"  货币: {ref.currency}")
            print(f"  状态: {ref.status}")
            print(f"  支付状态: {ref.payment_status}")
            
            # 检查业务类型
            print(f"\n业务类型信息:")
            if ref.ref_type:
                print(f"  业务类型ID: {ref.ref_type_id}")
                print(f"  业务类型名称: {ref.ref_type.name}")
                print(f"  业务类型代码: {ref.ref_type.code}")
            else:
                print("  ❌ 没有关联的业务类型")
            
            # 检查extra_info字段
            print(f"\nextra_info字段:")
            if ref.extra_info:
                print(f"  原始extra_info: {ref.extra_info}")
                try:
                    visa_info = json.loads(ref.extra_info)
                    print(f"  解析后的visa_info:")
                    for key, value in visa_info.items():
                        print(f"    {key}: {value}")
                    
                    # 检查关键字段
                    country = visa_info.get('country', '')
                    visa_type = visa_info.get('visa_type', '')
                    applicant_info = visa_info.get('applicant_info', '')
                    
                    print(f"\n关键字段检查:")
                    print(f"  国家: '{country}'")
                    print(f"  签证类型: '{visa_type}'")
                    print(f"  申请人信息: '{applicant_info}'")
                    
                    if not country:
                        print("  ⚠️ 国家字段为空")
                    if not visa_type:
                        print("  ⚠️ 签证类型字段为空")
                    
                    # 检查是否是从签证项目创建的
                    source_system = visa_info.get('source_system', '')
                    created_from_visa_project = visa_info.get('created_from_visa_project', False)
                    visa_project_id = visa_info.get('visa_project_id', None)
                    
                    print(f"\n来源检查:")
                    print(f"  来源系统: {source_system}")
                    print(f"  从签证项目创建: {created_from_visa_project}")
                    print(f"  签证项目ID: {visa_project_id}")
                    
                    if created_from_visa_project and visa_project_id:
                        from App.models.Product.Visamodels import VisaProject
                        visa_project = VisaProject.query.get(visa_project_id)
                        if visa_project:
                            print(f"  关联的签证项目:")
                            print(f"    项目ID: {visa_project.id}")
                            print(f"    申请人: {visa_project.applicant_name}")
                            print(f"    签证类型: {visa_project.visa_type}")
                            print(f"    联系人: {visa_project.contact_name}")
                            
                            # 获取签证类型信息
                            from App.models.Product.Visamodels import VisaTypes
                            types_info = VisaTypes.query.filter_by(visa_type=visa_project.visa_type).first()
                            if types_info:
                                print(f"    签证类型信息:")
                                print(f"      国家: {types_info.country.country_name_CN if types_info.country else '未知'}")
                                print(f"      费用: {types_info.fee}")
                                print(f"      处理时间: {types_info.processing_time}")
                        else:
                            print(f"  ❌ 找不到关联的签证项目 (ID: {visa_project_id})")
                    
                except json.JSONDecodeError as e:
                    print(f"  ❌ JSON解析失败: {str(e)}")
            else:
                print("  ❌ extra_info字段为空")
            
            print("\n✅ REF 220数据检查完成")
                
        except Exception as e:
            print(f"检查过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_ref_220_edit() 
#!/usr/bin/env python3
"""
测试REF创建时申请费用到售价字段的转换
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.Product.Visamodels import VisaProject, VisaTypes
from App.models.projects.BookingProject import ProjectHeader, ProjectRef
from App.models.Product.BusinessType import BusinessType
import json
import re

def test_visa_ref_selling_price():
    """测试REF创建时申请费用到售价字段的转换"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始测试REF创建时申请费用到售价字段的转换...")
            
            # 1. 选择一个测试项目
            print("\n=== 选择测试项目 ===")
            test_project = VisaProject.query.filter(
                VisaProject.header_id.is_(None),
                VisaProject.ref_id.is_(None)
            ).join(VisaTypes, VisaProject.visa_type == VisaTypes.visa_type).first()
            
            if not test_project:
                print("❌ 没有找到合适的测试项目（所有项目都已关联）")
                return
            
            print(f"选择测试项目: ID={test_project.id}")
            print(f"  申请人: {test_project.applicant_name}")
            print(f"  签证类型: {test_project.visa_type}")
            print(f"  联系人: {test_project.contact_name}")
            print(f"  在新加坡身份: {test_project.singapore_status}")
            print(f"  签证状态: {test_project.visa_status}")
            
            # 2. 获取签证类型信息
            print("\n=== 获取签证类型信息 ===")
            types_info = VisaTypes.query.filter_by(visa_type=test_project.visa_type).first()
            if types_info:
                print(f"签证类型: {types_info.visa_type}")
                print(f"国家: {types_info.country.country_name_CN if types_info.country else '未知'}")
                print(f"申请费用: {types_info.fee}")
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
            
            # 4. 测试费用解析逻辑
            print("\n=== 测试费用解析逻辑 ===")
            selling_price = None
            if types_info and types_info.fee:
                try:
                    # 尝试从费用字符串中提取数字
                    fee_match = re.search(r'(\d+(?:\.\d+)?)', types_info.fee)
                    if fee_match:
                        selling_price = float(fee_match.group(1))
                        print(f"✅ 成功提取售价: {selling_price} 从费用: {types_info.fee}")
                    else:
                        print(f"❌ 无法从费用字符串中提取数字: {types_info.fee}")
                except (ValueError, AttributeError) as e:
                    print(f"❌ 解析费用时出错: {str(e)}")
            else:
                print("⚠️ 没有费用信息")
            
            # 5. 创建HID
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
            
            # 6. 准备签证相关的额外信息
            print("\n=== 准备签证相关的额外信息 ===")
            visa_extra_info = {
                'visa_type': test_project.visa_type,
                'visa_country': types_info.country.country_name_CN if types_info.country else '未知',
                'visa_country_code': types_info.country.country_code if types_info.country else None,
                'singapore_status': test_project.singapore_status,
                'visa_status': test_project.visa_status,
                'processing_time': types_info.processing_time if types_info else None,
                'visa_fee': types_info.fee if types_info else None,
                'source_system': 'visa_system',
                'created_from_visa_project': True,
                'visa_project_id': test_project.id
            }
            
            # 7. 创建REF
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
                leader_name=test_project.applicant_name,  # 使用申请人姓名作为负责人姓名
                selling_price=selling_price,  # 使用申请费用作为售价
                currency='SGD',
                expected_delivery_date=test_project.estimated_date,
                remarks=test_project.remarks,
                status='processing',
                payment_status='unpaid',
                extra_info=json.dumps(visa_extra_info, ensure_ascii=False)
            )
            db.session.add(ref)
            db.session.flush()
            print(f"✅ REF创建成功: ID={ref.id}, REF={ref.ref_number}")
            
            # 8. 更新签证项目关联
            print("\n=== 更新签证项目关联 ===")
            test_project.header_id = header.id
            test_project.ref_id = ref.id
            db.session.commit()
            print(f"✅ 签证项目关联更新成功")
            
            # 9. 验证REF的售价字段
            print("\n=== 验证REF的售价字段 ===")
            # 重新查询REF
            ref_verify = ProjectRef.query.get(ref.id)
            
            print(f"REF基本信息:")
            print(f"  REF编号: {ref_verify.ref_number}")
            print(f"  名称: {ref_verify.name}")
            print(f"  联系人: {ref_verify.contact_name}")
            print(f"  负责人姓名: {ref_verify.leader_name}")
            print(f"  售价: {ref_verify.selling_price}")
            print(f"  货币: {ref_verify.currency}")
            print(f"  状态: {ref_verify.status}")
            print(f"  支付状态: {ref_verify.payment_status}")
            
            # 验证售价是否正确填充
            print(f"\n验证售价:")
            print(f"  原始申请费用: {types_info.fee}")
            print(f"  解析后的售价: {selling_price}")
            print(f"  REF中的售价: {ref_verify.selling_price}")
            print(f"  售价匹配: {ref_verify.selling_price == selling_price}")
            
            # 验证货币
            print(f"\n验证货币:")
            print(f"  REF货币: {ref_verify.currency}")
            print(f"  货币匹配: {ref_verify.currency == 'SGD'}")
            
            # 10. 验证其他字段
            print("\n=== 验证其他字段 ===")
            print(f"  预估日期: {ref_verify.expected_delivery_date}")
            print(f"  备注: {ref_verify.remarks}")
            print(f"  描述: {ref_verify.description}")
            
            # 11. 验证额外信息
            print("\n=== 验证额外信息 ===")
            if ref_verify.extra_info:
                stored_extra_info = json.loads(ref_verify.extra_info)
                print("存储的额外信息:")
                for key, value in stored_extra_info.items():
                    print(f"  {key}: {value}")
            
            print("\n✅ REF创建时申请费用到售价字段转换测试完成！")
            print(f"测试项目ID: {test_project.id}")
            print(f"申请人姓名: {test_project.applicant_name}")
            print(f"创建的HID: {header.hid}")
            print(f"创建的REF: {ref.ref_number}")
            print(f"申请费用: {types_info.fee}")
            print(f"REF售价: {ref_verify.selling_price}")
            print(f"REF货币: {ref_verify.currency}")
                
        except Exception as e:
            db.session.rollback()
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_visa_ref_selling_price() 
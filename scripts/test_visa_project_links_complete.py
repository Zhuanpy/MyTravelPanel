#!/usr/bin/env python3
"""
完整测试签证项目HID和REF创建功能，包括签证国家和签证类型信息的存储
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.Product.Visamodels import VisaProject, VisaTypes
from App.models.projects.BookingProject import ProjectHeader, ProjectRef
from App.models.Product.BusinessType import BusinessType
import json

def test_visa_project_links_complete():
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
            ).join(VisaTypes, VisaProject.visa_type == VisaTypes.visa_type).first()
            
            if not test_project:
                print("❌ 没有找到合适的测试项目（所有项目都已关联）")
                return
            
            print(f"选择测试项目: ID={test_project.id}")
            print(f"  申请人: {test_project.applicant_name}")
            print(f"  签证类型: {test_project.visa_type}")
            print(f"  在新加坡身份: {test_project.singapore_status}")
            print(f"  签证状态: {test_project.visa_status}")
            print(f"  联系人: {test_project.contact_name}")
            print(f"  预估日期: {test_project.estimated_date}")
            print(f"  备注: {test_project.remarks}")
            
            # 2. 获取签证类型信息
            print("\n=== 获取签证类型信息 ===")
            types_info = VisaTypes.query.filter_by(visa_type=test_project.visa_type).first()
            if types_info:
                print(f"签证类型: {types_info.visa_type}")
                print(f"国家: {types_info.country.country_name_CN if types_info.country else '未知'}")
                print(f"国家代码: {types_info.country.country_code if types_info.country else '未知'}")
                print(f"处理时间: {types_info.processing_time}")
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
            
            # 5. 准备签证相关的额外信息
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
            
            print("签证额外信息:")
            for key, value in visa_extra_info.items():
                print(f"  {key}: {value}")
            
            # 6. 创建REF
            print("\n=== 创建REF ===")
            ref_number = ProjectRef.generate_ref_number(header.hid)
            print(f"生成的REF: {ref_number}")
            
            # 解析申请费用，提取数字部分
            selling_price = None
            if types_info and types_info.fee:
                try:
                    # 尝试从费用字符串中提取数字
                    import re
                    fee_match = re.search(r'(\d+(?:\.\d+)?)', types_info.fee)
                    if fee_match:
                        selling_price = float(fee_match.group(1))
                        print(f"DEBUG: Extracted selling price: {selling_price} from fee: {types_info.fee}")
                except (ValueError, AttributeError) as e:
                    print(f"DEBUG: Failed to extract selling price from fee '{types_info.fee}': {str(e)}")
            
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
            
            # 7. 更新签证项目关联
            print("\n=== 更新签证项目关联 ===")
            test_project.header_id = header.id
            test_project.ref_id = ref.id
            db.session.commit()
            print(f"✅ 签证项目关联更新成功")
            
            # 8. 验证关联结果
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
            
            # 9. 验证项目主表和REF明细
            print("\n=== 验证项目主表和REF明细 ===")
            header_verify = ProjectHeader.query.get(header.id)
            ref_verify = ProjectRef.query.get(ref.id)
            
            print(f"项目主表验证:")
            print(f"  HID: {header_verify.hid}")
            print(f"  描述: {header_verify.desc}")
            print(f"  联系人: {header_verify.contact}")
            print(f"  国家: {header_verify.country}")
            print(f"  类型: {header_verify.type}")
            print(f"  来源: {header_verify.source}")
            print(f"  状态: {header_verify.status}")
            
            print(f"REF明细验证:")
            print(f"  REF编号: {ref_verify.ref_number}")
            print(f"  名称: {ref_verify.name}")
            print(f"  描述: {ref_verify.description}")
            print(f"  联系人: {ref_verify.contact_name}")
            print(f"  负责人姓名: {ref_verify.leader_name}")
            print(f"  售价: {ref_verify.selling_price}")
            print(f"  货币: {ref_verify.currency}")
            print(f"  预估日期: {ref_verify.expected_delivery_date}")
            print(f"  备注: {ref_verify.remarks}")
            print(f"  状态: {ref_verify.status}")
            print(f"  支付状态: {ref_verify.payment_status}")
            
            # 验证售价
            print(f"\n验证售价:")
            print(f"  原始申请费用: {types_info.fee if types_info else '无'}")
            print(f"  REF售价: {ref_verify.selling_price}")
            print(f"  REF货币: {ref_verify.currency}")
            if types_info and types_info.fee:
                import re
                fee_match = re.search(r'(\d+(?:\.\d+)?)', types_info.fee)
                if fee_match:
                    expected_price = float(fee_match.group(1))
                    print(f"  预期售价: {expected_price}")
                    print(f"  售价匹配: {ref_verify.selling_price == expected_price}")
            
            # 验证负责人姓名
            print(f"\n验证负责人姓名:")
            print(f"  申请人姓名: {test_project.applicant_name}")
            print(f"  REF负责人姓名: {ref_verify.leader_name}")
            print(f"  负责人姓名匹配: {ref_verify.leader_name == test_project.applicant_name}")
            
            # 10. 验证REF的额外信息
            print("\n=== 验证REF的额外信息 ===")
            if ref_verify.extra_info:
                stored_extra_info = json.loads(ref_verify.extra_info)
                print("存储的额外信息:")
                for key, value in stored_extra_info.items():
                    print(f"  {key}: {value}")
                
                # 验证关键信息
                print("\n验证关键信息:")
                print(f"  签证类型匹配: {stored_extra_info.get('visa_type') == test_project.visa_type}")
                print(f"  签证国家匹配: {stored_extra_info.get('visa_country') == types_info.country.country_name_CN}")
                print(f"  国家代码匹配: {stored_extra_info.get('visa_country_code') == types_info.country.country_code}")
                print(f"  新加坡身份匹配: {stored_extra_info.get('singapore_status') == test_project.singapore_status}")
                print(f"  签证状态匹配: {stored_extra_info.get('visa_status') == test_project.visa_status}")
                print(f"  处理时间匹配: {stored_extra_info.get('processing_time') == types_info.processing_time}")
                print(f"  申请费用匹配: {stored_extra_info.get('visa_fee') == types_info.fee}")
                print(f"  来源系统: {stored_extra_info.get('source_system')}")
                print(f"  来自签证项目: {stored_extra_info.get('created_from_visa_project')}")
                print(f"  签证项目ID: {stored_extra_info.get('visa_project_id')}")
            else:
                print("❌ REF中没有存储额外信息")
            
            # 11. 验证数据完整性
            print("\n=== 验证数据完整性 ===")
            # 检查HID和REF的关联关系
            header_refs = header_verify.refs
            print(f"HID关联的REF数量: {len(header_refs)}")
            for ref_item in header_refs:
                print(f"  REF: {ref_item.ref_number}")
            
            # 检查签证项目是否可以通过关联访问HID和REF
            visa_project_with_links = VisaProject.query.get(test_project.id)
            print(f"签证项目可以通过关联访问HID: {visa_project_with_links.header is not None}")
            print(f"签证项目可以通过关联访问REF: {visa_project_with_links.ref is not None}")
            
            if visa_project_with_links.header:
                print(f"  关联的HID: {visa_project_with_links.header.hid}")
            if visa_project_with_links.ref:
                print(f"  关联的REF: {visa_project_with_links.ref.ref_number}")
            
            print("\n✅ 签证项目HID和REF创建功能完整测试完成！")
            print(f"测试项目ID: {test_project.id}")
            print(f"创建的HID: {header.hid}")
            print(f"创建的REF: {ref.ref_number}")
            print(f"签证类型: {test_project.visa_type}")
            print(f"签证国家: {types_info.country.country_name_CN if types_info.country else '未知'}")
            print(f"签证国家代码: {types_info.country.country_code if types_info.country else '未知'}")
            print(f"处理时间: {types_info.processing_time}")
            print(f"申请费用: {types_info.fee}")
                
        except Exception as e:
            db.session.rollback()
            print(f"测试过程中发生错误: {str(e)}")
            raise

if __name__ == '__main__':
    test_visa_project_links_complete() 
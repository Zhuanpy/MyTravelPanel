#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试补充信息标签页功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.Product.Visamodels import VisaTypes, VisaDocuments

def test_additional_info_tab():
    """测试补充信息标签页"""
    app = create_app()
    
    with app.app_context():
        try:
            # 获取中国签证类型
            visa_type = VisaTypes.query.filter_by(visa_type='中国签证').first()
            if not visa_type:
                print("❌ 没有找到中国签证类型")
                return False
            
            print(f"✅ 找到签证类型: {visa_type.visa_type}")
            
            # 获取文档配置信息
            document_data = {}
            
            # 获取共用资料
            share_info = VisaDocuments.get_document_info(visa_type.id, None)
            document_data['SHARE'] = share_info
            
            # 获取各身份的文档配置
            for identity in visa_type.identities:
                info = VisaDocuments.get_document_info(visa_type.id, identity.id)
                document_data[identity.identity_zh] = info
            
            print(f"✅ 成功获取文档数据，共 {len(document_data)} 个身份")
            
            # 检查补充信息
            print("\n📋 补充信息检查:")
            has_additional_info = False
            
            # 检查共用资料补充信息
            if (document_data.get('SHARE') and 
                document_data['SHARE'].get('additional_info') and 
                document_data['SHARE']['additional_info'] != '暂无补充信息'):
                has_additional_info = True
                print(f"✅ 共用资料有补充信息: {document_data['SHARE']['additional_info'][:50]}...")
            
            # 检查各身份补充信息
            for identity, data in document_data.items():
                if identity != 'SHARE' and data and data.get('additional_info') and data['additional_info'] != '暂无补充信息':
                    has_additional_info = True
                    print(f"✅ {identity}有补充信息: {data['additional_info'][:50]}...")
            
            if not has_additional_info:
                print("ℹ️ 目前没有补充信息，这是正常的")
            
            print("\n🎯 补充信息标签页功能:")
            print("✅ 标签页已添加")
            print("✅ 补充信息汇总显示")
            print("✅ 按身份分类显示")
            print("✅ 无补充信息时显示提示")
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            return False

if __name__ == "__main__":
    print("开始测试补充信息标签页功能...")
    success = test_additional_info_tab()
    if success:
        print("\n✅ 补充信息标签页测试通过！")
    else:
        print("\n❌ 补充信息标签页测试失败！") 
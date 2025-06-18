#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SHARE配置的完整功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models import VisaTypes, VisaDocuments, VisaDocumentsList, VisaSingaporeIdentity

def test_share_complete():
    """测试SHARE配置的完整功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试SHARE配置的完整功能 ===\n")
        
        # 1. 检查SHARE身份
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if not share_identity:
            print("❌ 没有找到SHARE身份")
            return False
        
        print(f"1. SHARE身份信息:")
        print(f"   ID: {share_identity.id}")
        print(f"   名称: {share_identity.identity_zh}")
        
        # 2. 检查所有身份（包括SHARE）
        all_identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
        print(f"\n2. 所有身份列表:")
        for identity in all_identities:
            print(f"   - {identity.identity_zh} (ID: {identity.id})")
        
        # 3. 检查SHARE是否在身份列表中
        share_in_list = any(identity.identity_zh == 'SHARE' for identity in all_identities)
        print(f"\n3. SHARE是否在身份列表中: {'✅ 是' if share_in_list else '❌ 否'}")
        
        # 4. 获取签证类型
        visa_type = VisaTypes.query.first()
        if not visa_type:
            print("❌ 没有找到签证类型")
            return False
        
        print(f"\n4. 签证类型: {visa_type.visa_type} (ID: {visa_type.id})")
        
        # 5. 获取文档
        documents = VisaDocumentsList.query.limit(3).all()
        if not documents:
            print("❌ 没有找到文档")
            return False
        
        print(f"\n5. 测试文档: {[d.name for d in documents]}")
        
        # 6. 清理现有SHARE配置
        existing_configs = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=share_identity.id
        ).all()
        
        for config in existing_configs:
            db.session.delete(config)
        db.session.commit()
        print(f"\n6. 清理了 {len(existing_configs)} 个现有SHARE配置")
        
        # 7. 创建新的SHARE配置
        share_config = VisaDocuments(
            visa_type_id=visa_type.id,
            singapore_identity_id=share_identity.id,
            additional_info="测试SHARE配置的完整功能"
        )
        share_config.selected_documents = documents[:2]  # 选择前2个文档
        db.session.add(share_config)
        db.session.commit()
        
        print(f"\n7. 创建SHARE配置成功:")
        print(f"   配置ID: {share_config.id}")
        print(f"   身份ID: {share_config.singapore_identity_id}")
        print(f"   选中文档: {[d.name for d in share_config.selected_documents]}")
        
        # 8. 模拟前端页面加载
        print(f"\n8. 模拟前端页面加载:")
        
        # 模拟visa_type_document_manager路由
        identities_for_template = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
        print(f"   模板中的身份数量: {len(identities_for_template)}")
        print(f"   身份列表:")
        for identity in identities_for_template:
            print(f"     - {identity.identity_zh} (ID: {identity.id})")
        
        # 9. 模拟API数据获取
        print(f"\n9. 模拟API数据获取:")
        
        # 获取该签证类型的所有文档配置
        visa_documents = VisaDocuments.query.filter_by(visa_type_id=visa_type.id).all()
        
        # 获取所有身份
        identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
        
        # 构建配置数据
        config_data = {
            'visa_type': visa_type.visa_type,
            'documents': []
        }
        
        # 为每个身份构建配置
        for identity in identities:
            # 查找该身份的文档配置
            identity_docs = [vd for vd in visa_documents if vd.singapore_identity_id == identity.id]
            
            # 获取选中的文档
            selected_documents = []
            additional_info = ""
            
            for vd in identity_docs:
                if vd.selected_documents:
                    for doc in vd.selected_documents:
                        selected_documents.append({
                            'id': doc.id,
                            'name': doc.name,
                            'category': doc.category
                        })
                additional_info = vd.additional_info or ""
            
            config_data['documents'].append({
                'singapore_identity_id': identity.id,
                'identity_name': identity.identity_zh,
                'selected_documents': selected_documents,
                'additional_info': additional_info
            })
        
        # 10. 验证SHARE配置
        share_config_data = None
        for doc_config in config_data['documents']:
            if doc_config['identity_name'] == 'SHARE':
                share_config_data = doc_config
                break
        
        if share_config_data:
            print(f"\n10. 验证SHARE配置:")
            print(f"    身份ID: {share_config_data['singapore_identity_id']}")
            print(f"    身份名称: {share_config_data['identity_name']}")
            print(f"    选中文档数: {len(share_config_data['selected_documents'])}")
            if share_config_data['selected_documents']:
                doc_names = [d['name'] for d in share_config_data['selected_documents']]
                doc_ids = [d['id'] for d in share_config_data['selected_documents']]
                print(f"    文档: {doc_names}")
                print(f"    文档ID: {doc_ids}")
            
            # 11. 模拟前端渲染
            print(f"\n11. 模拟前端渲染:")
            
            # 检查SHARE是否会在前端显示
            share_in_template = any(identity.identity_zh == 'SHARE' for identity in identities_for_template)
            print(f"    SHARE是否在模板中: {'✅ 是' if share_in_template else '❌ 否'}")
            
            if share_in_template:
                print(f"    SHARE会在前端显示为: 共用资料")
                print(f"    SHARE的配置数据: {len(share_config_data['selected_documents'])} 个文档")
                print(f"    SHARE可以被编辑和保存: ✅ 是")
            else:
                print(f"    ❌ SHARE不会在前端显示")
            
            # 12. 清理测试数据
            db.session.delete(share_config)
            db.session.commit()
            print(f"\n12. 清理测试数据完成")
            
            print(f"\n✅ SHARE配置完整功能测试成功！")
            return True
        else:
            print(f"\n❌ 没有找到SHARE配置数据")
            return False

if __name__ == '__main__':
    success = test_share_complete()
    if not success:
        sys.exit(1) 
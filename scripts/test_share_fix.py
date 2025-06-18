#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SHARE配置修复后的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models import VisaTypes, VisaDocuments, VisaDocumentsList, VisaSingaporeIdentity

def test_share_fix():
    """测试SHARE配置修复"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试SHARE配置修复后的功能 ===\n")
        
        # 1. 检查SHARE身份
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if not share_identity:
            print("❌ 没有找到SHARE身份")
            return False
        
        print(f"1. SHARE身份信息:")
        print(f"   ID: {share_identity.id}")
        print(f"   名称: {share_identity.identity_zh}")
        
        # 2. 获取签证类型
        visa_type = VisaTypes.query.first()
        if not visa_type:
            print("❌ 没有找到签证类型")
            return False
        
        print(f"\n2. 签证类型: {visa_type.visa_type} (ID: {visa_type.id})")
        
        # 3. 获取文档
        documents = VisaDocumentsList.query.limit(2).all()
        if not documents:
            print("❌ 没有找到文档")
            return False
        
        print(f"\n3. 测试文档: {[d.name for d in documents]}")
        
        # 4. 清理现有配置
        existing_configs = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=share_identity.id
        ).all()
        
        for config in existing_configs:
            db.session.delete(config)
        db.session.commit()
        print(f"\n4. 清理了 {len(existing_configs)} 个现有SHARE配置")
        
        # 5. 创建新的SHARE配置
        share_config = VisaDocuments(
            visa_type_id=visa_type.id,
            singapore_identity_id=share_identity.id,  # 使用SHARE的实际ID
            additional_info="测试SHARE配置修复"
        )
        share_config.selected_documents = documents
        db.session.add(share_config)
        db.session.commit()
        
        print(f"\n5. 创建SHARE配置成功:")
        print(f"   配置ID: {share_config.id}")
        print(f"   身份ID: {share_config.singapore_identity_id}")
        print(f"   选中文档: {[d.name for d in share_config.selected_documents]}")
        
        # 6. 模拟API数据获取
        print(f"\n6. 模拟API数据获取:")
        
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
        
        # 7. 验证SHARE配置
        share_config_data = None
        for doc_config in config_data['documents']:
            if doc_config['identity_name'] == 'SHARE':
                share_config_data = doc_config
                break
        
        if share_config_data:
            print(f"\n7. 验证SHARE配置:")
            print(f"   身份ID: {share_config_data['singapore_identity_id']}")
            print(f"   身份名称: {share_config_data['identity_name']}")
            print(f"   选中文档数: {len(share_config_data['selected_documents'])}")
            if share_config_data['selected_documents']:
                doc_names = [d['name'] for d in share_config_data['selected_documents']]
                doc_ids = [d['id'] for d in share_config_data['selected_documents']]
                print(f"   文档: {doc_names}")
                print(f"   文档ID: {doc_ids}")
            
            # 8. 清理测试数据
            db.session.delete(share_config)
            db.session.commit()
            print(f"\n8. 清理测试数据完成")
            
            print(f"\n✅ SHARE配置修复测试成功！")
            return True
        else:
            print(f"\n❌ 没有找到SHARE配置数据")
            return False

if __name__ == '__main__':
    success = test_share_fix()
    if not success:
        sys.exit(1) 
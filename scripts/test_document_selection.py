#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试签证文档管理器的数据加载和显示功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models import VisaTypes, VisaDocuments, VisaDocumentsList, VisaSingaporeIdentity

def test_document_selection():
    """测试文档选择功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试签证文档管理器的数据加载和显示功能 ===\n")
        
        # 1. 检查签证类型
        visa_types = VisaTypes.query.all()
        print(f"1. 找到 {len(visa_types)} 个签证类型:")
        for vt in visa_types[:3]:  # 只显示前3个
            print(f"   - {vt.visa_type} (ID: {vt.id})")
        
        if not visa_types:
            print("   没有找到签证类型，请先创建一些签证类型")
            return
        
        # 2. 选择一个签证类型进行测试
        test_visa_type = visa_types[0]
        print(f"\n2. 使用签证类型进行测试: {test_visa_type.visa_type}")
        
        # 3. 检查该签证类型的文档配置
        visa_documents = VisaDocuments.query.filter_by(visa_type_id=test_visa_type.id).all()
        print(f"\n3. 找到 {len(visa_documents)} 个文档配置记录:")
        
        for vd in visa_documents:
            identity_name = "SHARE" if vd.singapore_identity_id is None else f"身份ID: {vd.singapore_identity_id}"
            doc_count = len(vd.selected_documents) if vd.selected_documents else 0
            print(f"   - 配置ID: {vd.id}, 身份: {identity_name}, 选中文档数: {doc_count}")
            
            if vd.selected_documents:
                print(f"     选中文档:")
                for doc in vd.selected_documents:
                    print(f"       - {doc.name} (ID: {doc.id}, 分类: {doc.category})")
        
        # 4. 检查所有身份
        identities = VisaSingaporeIdentity.query.filter(VisaSingaporeIdentity.identity_zh != 'SHARE').all()
        print(f"\n4. 找到 {len(identities)} 个身份:")
        for identity in identities[:5]:  # 只显示前5个
            print(f"   - {identity.identity_zh} (ID: {identity.id})")
        
        # 5. 检查所有文档
        all_documents = VisaDocumentsList.query.all()
        print(f"\n5. 找到 {len(all_documents)} 个文档:")
        for doc in all_documents[:5]:  # 只显示前5个
            print(f"   - {doc.name} (ID: {doc.id}, 分类: {doc.category})")
        
        # 6. 模拟API数据获取
        print(f"\n6. 模拟API数据获取:")
        
        # 获取该签证类型的所有文档配置
        visa_documents = VisaDocuments.query.filter_by(visa_type_id=test_visa_type.id).all()
        
        # 获取所有身份
        identities = VisaSingaporeIdentity.query\
            .filter(VisaSingaporeIdentity.identity_zh != 'SHARE')\
            .order_by(VisaSingaporeIdentity.identity_zh)\
            .all()
        
        # 构建配置数据
        config_data = {
            'visa_type': test_visa_type.visa_type,
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
        
        # 添加SHARE配置
        share_docs = [vd for vd in visa_documents if vd.singapore_identity_id is None]
        selected_share_documents = []
        share_additional_info = ""
        
        for vd in share_docs:
            if vd.selected_documents:
                for doc in vd.selected_documents:
                    selected_share_documents.append({
                        'id': doc.id,
                        'name': doc.name,
                        'category': doc.category
                    })
            share_additional_info = vd.additional_info or ""
        
        config_data['documents'].insert(0, {
            'singapore_identity_id': None,
            'identity_name': 'SHARE',
            'selected_documents': selected_share_documents,
            'additional_info': share_additional_info
        })
        
        # 7. 显示模拟的配置数据
        print(f"\n7. 模拟的配置数据:")
        print(f"   签证类型: {config_data['visa_type']}")
        print(f"   配置数量: {len(config_data['documents'])}")
        
        for doc_config in config_data['documents']:
            identity_name = doc_config['identity_name']
            doc_count = len(doc_config['selected_documents'])
            print(f"   - {identity_name}: {doc_count} 个文档")
            if doc_config['selected_documents']:
                doc_names = [d['name'] for d in doc_config['selected_documents']]
                doc_ids = [d['id'] for d in doc_config['selected_documents']]
                print(f"     文档: {doc_names}")
                print(f"     文档ID: {doc_ids}")
        
        # 8. 检查前端渲染逻辑
        print(f"\n8. 前端渲染逻辑检查:")
        for doc_config in config_data['documents']:
            identity_name = doc_config['identity_name']
            selected_doc_ids = [d['id'] for d in doc_config['selected_documents']]
            
            print(f"   - {identity_name}:")
            print(f"     选中文档ID: {selected_doc_ids}")
            
            # 模拟前端检查逻辑
            for doc in all_documents[:3]:  # 检查前3个文档
                is_selected = selected_doc_ids.count(doc.id) > 0
                print(f"     文档 {doc.name} (ID: {doc.id}): {'选中' if is_selected else '未选中'}")
        
        print(f"\n=== 测试完成 ===")

if __name__ == '__main__':
    test_document_selection() 
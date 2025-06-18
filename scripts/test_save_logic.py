#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试保存逻辑，模拟前端发送数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models import VisaTypes, VisaDocuments, VisaDocumentsList, VisaSingaporeIdentity
from sqlalchemy import text

def test_save_logic():
    """测试保存逻辑"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试保存逻辑 ===\n")
        
        # 1. 获取测试数据
        china_visa = VisaTypes.query.filter_by(visa_type='中国签证').first()
        if not china_visa:
            print("❌ 没有找到中国签证类型")
            return False
        
        documents = VisaDocumentsList.query.limit(5).all()
        if not documents:
            print("❌ 没有找到文档")
            return False
        
        identities = VisaSingaporeIdentity.query.all()
        if not identities:
            print("❌ 没有找到身份")
            return False
        
        print(f"1. 测试数据:")
        print(f"   签证类型: {china_visa.visa_type} (ID: {china_visa.id})")
        print(f"   文档: {[d.name for d in documents]}")
        print(f"   身份: {[i.identity_zh for i in identities]}")
        
        # 2. 清理现有配置
        existing_configs = VisaDocuments.query.filter_by(visa_type_id=china_visa.id).all()
        for config in existing_configs:
            db.session.delete(config)
        db.session.commit()
        print(f"\n2. 清理了 {len(existing_configs)} 个现有配置")
        
        # 3. 模拟前端发送的数据
        print(f"\n3. 模拟前端发送的数据:")
        
        # 模拟前端数据收集逻辑
        identity_configs = []
        
        for identity in identities:
            # 模拟选择一些文档（每个身份选择不同的文档）
            selected_docs = documents[:2] if identity.identity_zh == 'SHARE' else documents[2:4]
            document_ids = [doc.id for doc in selected_docs]
            additional_info = f"测试{identity.identity_zh}配置"
            
            identity_configs.append({
                'identity_id': identity.id,
                'document_ids': document_ids,
                'additional_info': additional_info
            })
            
            print(f"   {identity.identity_zh}:")
            print(f"     - 身份ID: {identity.id}")
            print(f"     - 选中文档ID: {document_ids}")
            print(f"     - 选中文档: {[d.name for d in selected_docs]}")
            print(f"     - 补充信息: {additional_info}")
        
        # 4. 模拟后端保存逻辑
        print(f"\n4. 模拟后端保存逻辑:")
        
        # 获取现有配置
        existing_configs = VisaDocuments.query.filter_by(visa_type_id=china_visa.id).all()
        existing_configs_dict = {config.singapore_identity_id: config for config in existing_configs}
        
        print(f"   现有配置数: {len(existing_configs)}")
        
        # 处理每个身份配置
        for i, config in enumerate(identity_configs):
            identity_id = config.get('identity_id')
            document_ids = config.get('document_ids', [])
            additional_info = config.get('additional_info', '')
            
            print(f"   处理配置 {i+1} - identity_id: {identity_id}, document_ids: {document_ids}")
            
            # 处理identity_id，确保是整数
            processed_identity_id = None
            if identity_id is not None:
                try:
                    processed_identity_id = int(identity_id)
                except (ValueError, TypeError):
                    print(f"   ❌ 无效的identity_id: {identity_id}")
                    continue
            
            # 查找或创建VisaDocuments记录
            if processed_identity_id in existing_configs_dict:
                # 更新现有记录
                visa_doc = existing_configs_dict[processed_identity_id]
                visa_doc.additional_info = additional_info
                print(f"   更新现有配置 - ID: {visa_doc.id}")
            else:
                # 创建新记录
                visa_doc = VisaDocuments(
                    visa_type_id=china_visa.id,
                    singapore_identity_id=processed_identity_id,
                    additional_info=additional_info
                )
                db.session.add(visa_doc)
                db.session.flush()  # 获取ID
                print(f"   创建新配置 - ID: {visa_doc.id}")
            
            # 更新选中的文档（多对多关系）
            if document_ids:
                documents_to_set = VisaDocumentsList.query.filter(VisaDocumentsList.id.in_(document_ids)).all()
                # 清空现有文档并设置新文档
                visa_doc.selected_documents = documents_to_set
                print(f"   为配置 {i+1} 设置了 {len(documents_to_set)} 个文档")
                print(f"   文档: {[d.name for d in documents_to_set]}")
            else:
                # 如果没有选中文档，清空现有文档
                visa_doc.selected_documents = []
                print(f"   配置 {i+1} 没有选中文档，已清空")
        
        db.session.commit()
        print(f"   配置保存成功")
        
        # 5. 验证保存结果
        print(f"\n5. 验证保存结果:")
        
        # 查询关联表
        query = text("""
            SELECT 
                vdd.visa_document_id,
                vdd.document_id,
                vdl.name as document_name,
                vd.singapore_identity_id,
                vsi.identity_zh as identity_name
            FROM visa_document_documents vdd
            JOIN visa_documents_list vdl ON vdd.document_id = vdl.id
            JOIN visa_documents_request vd ON vdd.visa_document_id = vd.id
            LEFT JOIN visa_singapore_identity vsi ON vd.singapore_identity_id = vsi.id
            WHERE vd.visa_type_id = :visa_type_id
            ORDER BY vd.singapore_identity_id, vdl.name
        """)
        
        result = db.session.execute(query, {'visa_type_id': china_visa.id})
        association_records = result.fetchall()
        
        print(f"   关联表记录数: {len(association_records)}")
        
        if association_records:
            print(f"   详细记录:")
            current_identity = None
            for record in association_records:
                identity_name = record.identity_name if record.identity_name else "SHARE"
                if identity_name != current_identity:
                    current_identity = identity_name
                    print(f"   \n   【{identity_name}】")
                print(f"     - {record.document_name} (文档ID: {record.document_id}, 配置ID: {record.visa_document_id})")
        else:
            print(f"   ❌ 关联表中没有数据")
        
        # 6. 验证通过关系查询
        print(f"\n6. 验证通过关系查询:")
        
        visa_docs = VisaDocuments.query.filter_by(visa_type_id=china_visa.id).all()
        for doc in visa_docs:
            identity_name = doc.singapore_identity.identity_zh if doc.singapore_identity else "SHARE"
            print(f"   {identity_name}:")
            print(f"     - 配置ID: {doc.id}")
            print(f"     - 选中文档数: {len(doc.selected_documents)}")
            if doc.selected_documents:
                for selected_doc in doc.selected_documents:
                    print(f"       * {selected_doc.name} (ID: {selected_doc.id})")
            else:
                print(f"       * 无选中文档")
            print(f"     - 补充信息: {doc.additional_info}")
        
        # 7. 清理测试数据
        for doc in visa_docs:
            db.session.delete(doc)
        db.session.commit()
        print(f"\n7. 清理测试数据完成")
        
        # 8. 总结
        print(f"\n8. 总结:")
        print(f"   - 处理了 {len(identity_configs)} 个身份配置")
        print(f"   - 关联表记录数: {len(association_records)}")
        print(f"   - 配置记录数: {len(visa_docs)}")
        
        if len(association_records) > 0:
            print(f"\n✅ 保存逻辑测试成功！文档数据正确保存到关联表")
            return True
        else:
            print(f"\n❌ 保存逻辑有问题，关联表中没有数据")
            return False

if __name__ == '__main__':
    success = test_save_logic()
    if not success:
        sys.exit(1) 
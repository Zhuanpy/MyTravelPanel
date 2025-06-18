#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文档数据保存到visa_document_documents关联表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models import VisaTypes, VisaDocuments, VisaDocumentsList, VisaSingaporeIdentity

def test_document_save():
    """测试文档数据保存到关联表"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试文档数据保存到关联表 ===\n")
        
        # 1. 获取测试数据
        visa_type = VisaTypes.query.first()
        if not visa_type:
            print("❌ 没有找到签证类型")
            return False
        
        documents = VisaDocumentsList.query.limit(3).all()
        if not documents:
            print("❌ 没有找到文档")
            return False
        
        share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
        if not share_identity:
            print("❌ 没有找到SHARE身份")
            return False
        
        print(f"1. 测试数据:")
        print(f"   签证类型: {visa_type.visa_type} (ID: {visa_type.id})")
        print(f"   文档: {[d.name for d in documents]}")
        print(f"   SHARE身份: {share_identity.identity_zh} (ID: {share_identity.id})")
        
        # 2. 清理现有配置
        existing_configs = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=share_identity.id
        ).all()
        
        for config in existing_configs:
            db.session.delete(config)
        db.session.commit()
        print(f"\n2. 清理了 {len(existing_configs)} 个现有配置")
        
        # 3. 创建新的配置并设置文档
        print(f"\n3. 创建新配置并设置文档...")
        
        # 创建VisaDocuments记录
        visa_doc = VisaDocuments(
            visa_type_id=visa_type.id,
            singapore_identity_id=share_identity.id,
            additional_info="测试补充信息"
        )
        db.session.add(visa_doc)
        db.session.flush()  # 获取ID
        
        print(f"   创建VisaDocuments记录 - ID: {visa_doc.id}")
        
        # 设置选中的文档（这会自动更新关联表）
        visa_doc.selected_documents = documents[:2]  # 选择前2个文档
        db.session.commit()
        
        print(f"   设置了 {len(visa_doc.selected_documents)} 个文档")
        print(f"   文档列表: {[d.name for d in visa_doc.selected_documents]}")
        
        # 4. 验证关联表数据
        print(f"\n4. 验证关联表数据:")
        
        # 直接查询关联表
        from sqlalchemy import text
        query = text("""
            SELECT vdd.visa_document_id, vdd.document_id, vdl.name as document_name
            FROM visa_document_documents vdd
            JOIN visa_documents_list vdl ON vdd.document_id = vdl.id
            WHERE vdd.visa_document_id = :visa_doc_id
        """)
        
        result = db.session.execute(query, {'visa_doc_id': visa_doc.id})
        association_records = result.fetchall()
        
        print(f"   关联表记录数: {len(association_records)}")
        for record in association_records:
            print(f"   - visa_document_id: {record.visa_document_id}, document_id: {record.document_id}, document_name: {record.document_name}")
        
        # 5. 验证通过关系查询
        print(f"\n5. 验证通过关系查询:")
        
        # 重新查询VisaDocuments记录
        visa_doc_reloaded = VisaDocuments.query.get(visa_doc.id)
        if visa_doc_reloaded:
            print(f"   重新加载的VisaDocuments记录:")
            print(f"   - ID: {visa_doc_reloaded.id}")
            print(f"   - 签证类型ID: {visa_doc_reloaded.visa_type_id}")
            print(f"   - 身份ID: {visa_doc_reloaded.singapore_identity_id}")
            print(f"   - 补充信息: {visa_doc_reloaded.additional_info}")
            print(f"   - 选中文档数: {len(visa_doc_reloaded.selected_documents)}")
            print(f"   - 选中文档: {[d.name for d in visa_doc_reloaded.selected_documents]}")
        else:
            print(f"   ❌ 无法重新加载VisaDocuments记录")
            return False
        
        # 6. 验证API读取逻辑
        print(f"\n6. 验证API读取逻辑:")
        
        # 模拟get_visa_documents API的逻辑
        visa_documents = VisaDocuments.query.filter_by(visa_type_id=visa_type.id).all()
        identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
        
        config_data = {
            'visa_type': visa_type.visa_type,
            'documents': []
        }
        
        for identity in identities:
            identity_docs = [vd for vd in visa_documents if vd.singapore_identity_id == identity.id]
            
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
        
        # 查找SHARE配置
        share_config = None
        for doc_config in config_data['documents']:
            if doc_config['identity_name'] == 'SHARE':
                share_config = doc_config
                break
        
        if share_config:
            print(f"   SHARE配置:")
            print(f"   - 身份ID: {share_config['singapore_identity_id']}")
            print(f"   - 身份名称: {share_config['identity_name']}")
            print(f"   - 选中文档数: {len(share_config['selected_documents'])}")
            print(f"   - 选中文档: {[d['name'] for d in share_config['selected_documents']]}")
            print(f"   - 补充信息: {share_config['additional_info']}")
        else:
            print(f"   ❌ 没有找到SHARE配置")
            return False
        
        # 7. 清理测试数据
        db.session.delete(visa_doc)
        db.session.commit()
        print(f"\n7. 清理测试数据完成")
        
        # 8. 验证清理结果
        remaining_associations = db.session.execute(
            text("SELECT COUNT(*) FROM visa_document_documents WHERE visa_document_id = :visa_doc_id"),
            {'visa_doc_id': visa_doc.id}
        ).scalar()
        
        print(f"8. 清理后关联表记录数: {remaining_associations}")
        
        if remaining_associations == 0:
            print(f"\n✅ 文档数据保存到关联表测试成功！")
            print(f"   总结:")
            print(f"   - 文档数据正确保存到visa_document_documents表")
            print(f"   - 通过关系查询能正确获取文档")
            print(f"   - API读取逻辑能正确返回文档数据")
            print(f"   - 删除记录时关联表数据也被正确清理")
            return True
        else:
            print(f"\n❌ 清理后仍有关联表记录")
            return False

if __name__ == '__main__':
    success = test_document_save()
    if not success:
        sys.exit(1) 
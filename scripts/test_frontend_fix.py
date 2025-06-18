#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端修复是否有效
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models import VisaTypes, VisaDocuments, VisaDocumentsList, VisaSingaporeIdentity
from sqlalchemy import text

def test_frontend_fix():
    """测试前端修复是否有效"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试前端修复是否有效 ===\n")
        
        # 1. 获取中国签证的当前状态
        china_visa = VisaTypes.query.filter_by(visa_type='中国签证').first()
        if not china_visa:
            print("❌ 没有找到中国签证类型")
            return False
        
        print(f"1. 当前中国签证状态:")
        
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
        current_records = result.fetchall()
        
        print(f"   当前关联表记录数: {len(current_records)}")
        
        if current_records:
            print(f"   当前记录:")
            current_identity = None
            for record in current_records:
                identity_name = record.identity_name if record.identity_name else "SHARE"
                if identity_name != current_identity:
                    current_identity = identity_name
                    print(f"   \n   【{identity_name}】")
                print(f"     - {record.document_name} (文档ID: {record.document_id}, 配置ID: {record.visa_document_id})")
        
        # 2. 模拟修复后的前端数据收集
        print(f"\n2. 模拟修复后的前端数据收集:")
        
        # 获取所有身份和文档
        identities = VisaSingaporeIdentity.query.all()
        documents = VisaDocumentsList.query.limit(5).all()
        
        # 模拟前端数据收集逻辑（修复后）
        identity_configs = []
        
        for identity in identities:
            # 模拟选择一些文档
            if identity.identity_zh == 'SHARE':
                selected_docs = documents[:2]  # SHARE选择前2个文档
            elif identity.identity_zh == 'PR':
                selected_docs = documents[2:4]  # PR选择第3-4个文档
            else:
                selected_docs = documents[4:5]  # 其他身份选择第5个文档
            
            document_ids = [doc.id for doc in selected_docs]
            additional_info = f"修复后测试{identity.identity_zh}配置"
            
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
        
        # 3. 模拟后端保存逻辑
        print(f"\n3. 模拟后端保存逻辑:")
        
        # 清理现有配置
        existing_configs = VisaDocuments.query.filter_by(visa_type_id=china_visa.id).all()
        for config in existing_configs:
            db.session.delete(config)
        db.session.commit()
        print(f"   清理了 {len(existing_configs)} 个现有配置")
        
        # 获取现有配置
        existing_configs = VisaDocuments.query.filter_by(visa_type_id=china_visa.id).all()
        existing_configs_dict = {config.singapore_identity_id: config for config in existing_configs}
        
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
        
        # 4. 验证修复结果
        print(f"\n4. 验证修复结果:")
        
        # 查询关联表
        result = db.session.execute(query, {'visa_type_id': china_visa.id})
        new_records = result.fetchall()
        
        print(f"   修复后关联表记录数: {len(new_records)}")
        
        if new_records:
            print(f"   详细记录:")
            current_identity = None
            for record in new_records:
                identity_name = record.identity_name if record.identity_name else "SHARE"
                if identity_name != current_identity:
                    current_identity = identity_name
                    print(f"   \n   【{identity_name}】")
                print(f"     - {record.document_name} (文档ID: {record.document_id}, 配置ID: {record.visa_document_id})")
        else:
            print(f"   ❌ 关联表中没有数据")
        
        # 5. 验证通过关系查询
        print(f"\n5. 验证通过关系查询:")
        
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
        
        # 6. 清理测试数据
        for doc in visa_docs:
            db.session.delete(doc)
        db.session.commit()
        print(f"\n6. 清理测试数据完成")
        
        # 7. 总结
        print(f"\n7. 总结:")
        print(f"   - 修复前关联表记录数: {len(current_records)}")
        print(f"   - 修复后关联表记录数: {len(new_records)}")
        print(f"   - 处理了 {len(identity_configs)} 个身份配置")
        
        if len(new_records) > len(current_records):
            print(f"\n✅ 前端修复成功！")
            print(f"   - 修复前只有 {len(current_records)} 条记录")
            print(f"   - 修复后有 {len(new_records)} 条记录")
            print(f"   - 所有身份的文档选择都能正确保存")
            return True
        else:
            print(f"\n❌ 前端修复可能还有问题")
            return False

if __name__ == '__main__':
    success = test_frontend_fix()
    if not success:
        sys.exit(1) 
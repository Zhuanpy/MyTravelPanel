#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查中国签证的文档配置和visa_document_documents表中的数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models import VisaTypes, VisaDocuments, VisaDocumentsList, VisaSingaporeIdentity
from sqlalchemy import text

def check_china_visa_documents():
    """检查中国签证的文档配置"""
    app = create_app()
    
    with app.app_context():
        print("=== 检查中国签证的文档配置 ===\n")
        
        # 1. 查找中国签证类型
        china_visa = VisaTypes.query.filter_by(visa_type='中国签证').first()
        if not china_visa:
            print("❌ 没有找到'中国签证'类型")
            # 列出所有签证类型
            all_visa_types = VisaTypes.query.all()
            print("可用的签证类型:")
            for vt in all_visa_types:
                print(f"  - {vt.visa_type}")
            return False
        
        print(f"1. 找到中国签证类型:")
        print(f"   ID: {china_visa.id}")
        print(f"   名称: {china_visa.visa_type}")
        
        # 2. 检查visa_documents_request表中的配置
        print(f"\n2. 检查visa_documents_request表中的配置:")
        
        visa_docs = VisaDocuments.query.filter_by(visa_type_id=china_visa.id).all()
        print(f"   找到 {len(visa_docs)} 个配置记录")
        
        for doc in visa_docs:
            identity_name = doc.singapore_identity.identity_zh if doc.singapore_identity else "SHARE"
            print(f"   - ID: {doc.id}, 身份: {identity_name}, 补充信息: {doc.additional_info}")
        
        # 3. 检查visa_document_documents关联表
        print(f"\n3. 检查visa_document_documents关联表:")
        
        # 查询关联表数据
        query = text("""
            SELECT 
                vdd.visa_document_id,
                vdd.document_id,
                vdl.name as document_name,
                vdl.category as document_category,
                vd.visa_type_id,
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
        
        print(f"   关联表中有 {len(association_records)} 条记录")
        
        if association_records:
            print(f"   详细记录:")
            current_identity = None
            for record in association_records:
                identity_name = record.identity_name if record.identity_name else "SHARE"
                if identity_name != current_identity:
                    current_identity = identity_name
                    print(f"   \n   【{identity_name}】")
                print(f"     - 文档: {record.document_name} (ID: {record.document_id}, 分类: {record.document_category})")
        else:
            print(f"   ❌ 关联表中没有找到中国签证的文档配置")
        
        # 4. 检查通过关系查询的结果
        print(f"\n4. 检查通过关系查询的结果:")
        
        for doc in visa_docs:
            identity_name = doc.singapore_identity.identity_zh if doc.singapore_identity else "SHARE"
            print(f"   {identity_name}:")
            print(f"     - 配置ID: {doc.id}")
            print(f"     - 选中文档数: {len(doc.selected_documents)}")
            if doc.selected_documents:
                for selected_doc in doc.selected_documents:
                    print(f"       * {selected_doc.name} (ID: {selected_doc.id}, 分类: {selected_doc.category})")
            else:
                print(f"       * 无选中文档")
            print(f"     - 补充信息: {doc.additional_info}")
        
        # 5. 检查所有身份
        print(f"\n5. 检查所有身份:")
        all_identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
        for identity in all_identities:
            print(f"   - {identity.identity_zh} (ID: {identity.id})")
        
        # 6. 检查是否有缺失的配置
        print(f"\n6. 检查缺失的配置:")
        configured_identity_ids = {doc.singapore_identity_id for doc in visa_docs if doc.singapore_identity_id is not None}
        all_identity_ids = {identity.id for identity in all_identities}
        
        missing_identities = all_identity_ids - configured_identity_ids
        if missing_identities:
            print(f"   缺失配置的身份:")
            for identity_id in missing_identities:
                identity = VisaSingaporeIdentity.query.get(identity_id)
                print(f"     - {identity.identity_zh} (ID: {identity_id})")
        else:
            print(f"   ✅ 所有身份都有配置")
        
        # 7. 总结
        print(f"\n7. 总结:")
        print(f"   - 中国签证类型ID: {china_visa.id}")
        print(f"   - 配置记录数: {len(visa_docs)}")
        print(f"   - 关联表记录数: {len(association_records)}")
        print(f"   - 总身份数: {len(all_identities)}")
        print(f"   - 已配置身份数: {len(configured_identity_ids)}")
        print(f"   - 缺失配置身份数: {len(missing_identities)}")
        
        if len(association_records) == 0:
            print(f"\n❌ 问题: 关联表中没有文档数据，说明文档选择没有正确保存")
        else:
            print(f"\n✅ 关联表中有文档数据，配置正常")
        
        return True

if __name__ == '__main__':
    check_china_visa_documents() 
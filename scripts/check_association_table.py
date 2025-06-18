#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门检查visa_document_documents关联表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from sqlalchemy import text

def check_association_table():
    """检查visa_document_documents关联表"""
    app = create_app()
    
    with app.app_context():
        print("=== 检查visa_document_documents关联表 ===\n")
        
        # 1. 检查关联表是否存在
        print("1. 检查关联表结构:")
        try:
            result = db.session.execute(text("SHOW TABLES LIKE 'visa_document_documents'"))
            table_exists = result.fetchone()
            if table_exists:
                print("   ✅ visa_document_documents表存在")
            else:
                print("   ❌ visa_document_documents表不存在")
                return False
        except Exception as e:
            print(f"   ❌ 检查表时出错: {e}")
            return False
        
        # 2. 检查关联表的所有数据
        print(f"\n2. 检查关联表的所有数据:")
        try:
            query = text("""
                SELECT 
                    vdd.visa_document_id,
                    vdd.document_id,
                    vdl.name as document_name,
                    vd.visa_type_id,
                    vt.visa_type,
                    vd.singapore_identity_id,
                    vsi.identity_zh as identity_name
                FROM visa_document_documents vdd
                JOIN visa_documents_list vdl ON vdd.document_id = vdl.id
                JOIN visa_documents_request vd ON vdd.visa_document_id = vd.id
                JOIN visa_types vt ON vd.visa_type_id = vt.id
                LEFT JOIN visa_singapore_identity vsi ON vd.singapore_identity_id = vsi.id
                ORDER BY vt.visa_type, vsi.identity_zh, vdl.name
            """)
            
            result = db.session.execute(query)
            all_records = result.fetchall()
            
            print(f"   关联表中共有 {len(all_records)} 条记录")
            
            if all_records:
                print(f"   详细记录:")
                current_visa_type = None
                current_identity = None
                
                for record in all_records:
                    visa_type = record.visa_type
                    identity_name = record.identity_name if record.identity_name else "SHARE"
                    
                    if visa_type != current_visa_type:
                        current_visa_type = visa_type
                        current_identity = None
                        print(f"   \n   【{visa_type}】")
                    
                    if identity_name != current_identity:
                        current_identity = identity_name
                        print(f"     {identity_name}:")
                    
                    print(f"       - {record.document_name} (文档ID: {record.document_id}, 配置ID: {record.visa_document_id})")
            else:
                print(f"   ❌ 关联表中没有任何数据")
        except Exception as e:
            print(f"   ❌ 查询关联表时出错: {e}")
            return False
        
        # 3. 检查中国签证的关联数据
        print(f"\n3. 专门检查中国签证的关联数据:")
        try:
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
                WHERE vd.visa_type_id = (SELECT id FROM visa_types WHERE visa_type = '中国签证')
                ORDER BY vd.singapore_identity_id, vdl.name
            """)
            
            result = db.session.execute(query)
            china_records = result.fetchall()
            
            print(f"   中国签证的关联记录数: {len(china_records)}")
            
            if china_records:
                print(f"   详细记录:")
                current_identity = None
                for record in china_records:
                    identity_name = record.identity_name if record.identity_name else "SHARE"
                    if identity_name != current_identity:
                        current_identity = identity_name
                        print(f"   \n   【{identity_name}】")
                    print(f"     - {record.document_name} (文档ID: {record.document_id}, 配置ID: {record.visa_document_id})")
            else:
                print(f"   ❌ 中国签证在关联表中没有数据")
        except Exception as e:
            print(f"   ❌ 查询中国签证关联数据时出错: {e}")
            return False
        
        # 4. 检查visa_documents_request表中的配置
        print(f"\n4. 检查visa_documents_request表中的配置:")
        try:
            query = text("""
                SELECT 
                    vd.id,
                    vd.visa_type_id,
                    vt.visa_type,
                    vd.singapore_identity_id,
                    vsi.identity_zh as identity_name,
                    vd.additional_info
                FROM visa_documents_request vd
                JOIN visa_types vt ON vd.visa_type_id = vt.id
                LEFT JOIN visa_singapore_identity vsi ON vd.singapore_identity_id = vsi.id
                WHERE vt.visa_type = '中国签证'
                ORDER BY vd.singapore_identity_id
            """)
            
            result = db.session.execute(query)
            config_records = result.fetchall()
            
            print(f"   中国签证的配置记录数: {len(config_records)}")
            
            for record in config_records:
                identity_name = record.identity_name if record.identity_name else "SHARE"
                print(f"   - 配置ID: {record.id}, 身份: {identity_name}, 补充信息: {record.additional_info}")
        except Exception as e:
            print(f"   ❌ 查询配置记录时出错: {e}")
            return False
        
        # 5. 总结
        print(f"\n5. 总结:")
        print(f"   - 关联表总记录数: {len(all_records)}")
        print(f"   - 中国签证关联记录数: {len(china_records)}")
        print(f"   - 中国签证配置记录数: {len(config_records)}")
        
        if len(china_records) == 0:
            print(f"\n❌ 问题确认: 中国签证在关联表中没有文档数据")
            print(f"   这说明文档选择没有正确保存到关联表中")
        else:
            print(f"\n✅ 中国签证在关联表中有文档数据")
        
        return True

if __name__ == '__main__':
    check_association_table() 
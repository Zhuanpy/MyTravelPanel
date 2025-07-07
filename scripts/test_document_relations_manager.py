#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试签证文档关联关系管理功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models.visa_models import (
    VisaTypes, VisaCountries, VisaSingaporeIdentity, 
    VisaDocuments, VisaDocumentsList, VisaDocumentDocuments
)

def test_document_relations_manager():
    """测试文档关联关系管理功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试签证文档关联关系管理功能 ===\n")
        
        try:
            # 1. 测试获取所有签证类型
            print("1. 获取所有签证类型:")
            visa_types = VisaTypes.query.order_by(VisaTypes.visa_type).all()
            print(f"   找到 {len(visa_types)} 个签证类型")
            for vt in visa_types[:5]:  # 只显示前5个
                print(f"   - {vt.visa_type}")
            if len(visa_types) > 5:
                print(f"   ... 还有 {len(visa_types) - 5} 个")
            print()
            
            # 2. 测试获取所有文档
            print("2. 获取所有文档:")
            documents = VisaDocumentsList.query.order_by(VisaDocumentsList.name).all()
            print(f"   找到 {len(documents)} 个文档")
            for doc in documents[:5]:  # 只显示前5个
                print(f"   - {doc.name} ({doc.category})")
            if len(documents) > 5:
                print(f"   ... 还有 {len(documents) - 5} 个")
            print()
            
            # 3. 测试获取所有身份
            print("3. 获取所有身份:")
            identities = VisaSingaporeIdentity.query.order_by(VisaSingaporeIdentity.identity_zh).all()
            print(f"   找到 {len(identities)} 个身份")
            for identity in identities[:5]:  # 只显示前5个
                print(f"   - {identity.identity_zh}")
            if len(identities) > 5:
                print(f"   ... 还有 {len(identities) - 5} 个")
            print()
            
            # 4. 测试获取关联关系数据
            print("4. 获取关联关系数据:")
            from sqlalchemy import text
            
            sql = text("""
                SELECT 
                    vdd.visa_document_id,
                    vdd.document_id,
                    vdd.responsible_party,
                    vt.visa_type,
                    vc.country_name_CN,
                    vsi.identity_zh,
                    vdl.name as document_name,
                    vdl.category as document_category
                FROM visa_document_documents vdd
                JOIN visa_documents_request vdr ON vdd.visa_document_id = vdr.id
                JOIN visa_types vt ON vdr.visa_type_id = vt.id
                JOIN visa_countries vc ON vt.country_id = vc.id
                LEFT JOIN visa_singapore_identity vsi ON vdr.singapore_identity_id = vsi.id
                JOIN visa_documents_list vdl ON vdd.document_id = vdl.id
                ORDER BY vt.visa_type, vsi.identity_zh, vdl.name
                LIMIT 10
            """)
            
            result = db.session.execute(sql)
            relations = []
            
            for row in result:
                relations.append({
                    'visa_document_id': row.visa_document_id,
                    'document_id': row.document_id,
                    'responsible_party': row.responsible_party,
                    'visa_type': row.visa_type,
                    'country_name': row.country_name_CN,
                    'identity_name': row.identity_zh or 'SHARE',
                    'document_name': row.document_name,
                    'document_category': row.document_category
                })
            
            print(f"   找到 {len(relations)} 条关联关系")
            for relation in relations:
                responsible_party_text = "申请人准备" if relation['responsible_party'] == 'FOR_APPLICATION' else "旅行社准备"
                print(f"   - {relation['visa_type']} ({relation['country_name']}) - {relation['identity_name']}")
                print(f"     文档: {relation['document_name']} ({relation['document_category']})")
                print(f"     准备方: {responsible_party_text}")
                print()
            
            # 5. 测试统计信息
            print("5. 统计信息:")
            
            # 按准备方统计
            sql_count = text("""
                SELECT 
                    responsible_party,
                    COUNT(*) as count
                FROM visa_document_documents
                GROUP BY responsible_party
            """)
            
            result = db.session.execute(sql_count)
            for row in result:
                party_text = "申请人准备" if row.responsible_party == 'FOR_APPLICATION' else "旅行社准备"
                print(f"   {party_text}: {row.count} 条")
            
            # 按签证类型统计
            sql_type_count = text("""
                SELECT 
                    vt.visa_type,
                    COUNT(*) as count
                FROM visa_document_documents vdd
                JOIN visa_documents_request vdr ON vdd.visa_document_id = vdr.id
                JOIN visa_types vt ON vdr.visa_type_id = vt.id
                GROUP BY vt.visa_type
                ORDER BY count DESC
                LIMIT 5
            """)
            
            result = db.session.execute(sql_type_count)
            print(f"\n   按签证类型统计 (前5名):")
            for row in result:
                print(f"   {row.visa_type}: {row.count} 条")
            
            print("\n=== 测试完成 ===")
            
        except Exception as e:
            print(f"测试过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()

def test_api_endpoints():
    """测试API端点"""
    app = create_app()
    
    with app.test_client() as client:
        print("\n=== 测试API端点 ===\n")
        
        # 1. 测试管理界面页面
        print("1. 测试管理界面页面:")
        response = client.get('/visa_basic/visa_document_relations_manager')
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ 页面加载成功")
        else:
            print("   ✗ 页面加载失败")
        print()
        
        # 2. 测试获取关联关系API
        print("2. 测试获取关联关系API:")
        response = client.get('/visa_basic/api/get_document_relations')
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            if data.get('success'):
                print(f"   ✓ 成功获取 {len(data.get('relations', []))} 条关联关系")
            else:
                print(f"   ✗ API返回错误: {data.get('message')}")
        else:
            print("   ✗ API请求失败")
        print()

if __name__ == '__main__':
    test_document_relations_manager()
    test_api_endpoints() 
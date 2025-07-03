#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试签证身份关联修复
验证 visa_type_identities 表和 VisaDocuments 表的数据一致性
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.Product.Visamodels import db, VisaTypes, VisaSingaporeIdentity, VisaDocuments
from sqlalchemy import text

def test_visa_identity_consistency():
    """测试签证身份关联的一致性"""
    app = create_app()
    
    with app.app_context():
        print("🔍 测试签证身份关联修复")
        print("=" * 50)
        
        # 1. 获取所有签证类型
        visa_types = VisaTypes.query.all()
        print(f"📋 找到 {len(visa_types)} 个签证类型")
        
        for vt in visa_types:
            print(f"\n🔸 签证类型: {vt.visa_type}")
            
            # 2. 从 visa_type_identities 表获取身份
            identities_from_relation = [identity.identity_zh for identity in vt.identities]
            print(f"   visa_type_identities表: {identities_from_relation}")
            
            # 3. 从 VisaDocuments 表获取身份
            docs = VisaDocuments.query.filter_by(visa_type_id=vt.id).all()
            identities_from_docs = []
            for doc in docs:
                if doc.singapore_identity_id:
                    identity = VisaSingaporeIdentity.query.get(doc.singapore_identity_id)
                    if identity:
                        identities_from_docs.append(identity.identity_zh)
                else:
                    identities_from_docs.append('SHARE')
            print(f"   VisaDocuments表: {identities_from_docs}")
            
            # 4. 检查一致性
            if set(identities_from_relation) == set([id for id in identities_from_docs if id != 'SHARE']):
                print(f"   ✅ 数据一致")
            else:
                print(f"   ❌ 数据不一致!")
                print(f"      差异: {set(identities_from_relation) ^ set([id for id in identities_from_docs if id != 'SHARE'])}")
        
        # 5. 检查数据库表结构
        print(f"\n🔍 检查数据库表结构")
        print("-" * 30)
        
        # 检查 visa_type_identities 表
        try:
            result = db.session.execute(text("""
                SELECT COUNT(*) as count FROM visa_type_identities
            """))
            count = result.fetchone()[0]
            print(f"   visa_type_identities表记录数: {count}")
        except Exception as e:
            print(f"   ❌ 查询visa_type_identities表失败: {e}")
        
        # 检查 visa_documents_request 表
        try:
            result = db.session.execute(text("""
                SELECT COUNT(*) as count FROM visa_documents_request
            """))
            count = result.fetchone()[0]
            print(f"   visa_documents_request表记录数: {count}")
        except Exception as e:
            print(f"   ❌ 查询visa_documents_request表失败: {e}")
        
        # 6. 显示详细的关联数据
        print(f"\n📊 详细关联数据")
        print("-" * 30)
        
        for vt in visa_types:
            print(f"\n🔸 {vt.visa_type}:")
            
            # visa_type_identities 表数据
            result = db.session.execute(text("""
                SELECT vsi.identity_zh 
                FROM visa_type_identities vti
                JOIN visa_singapore_identity vsi ON vti.identity_id = vsi.id
                WHERE vti.visa_type_id = :visa_type_id
            """), {'visa_type_id': vt.id})
            
            vti_identities = [row[0] for row in result.fetchall()]
            print(f"   visa_type_identities: {vti_identities}")
            
            # visa_documents_request 表数据
            result = db.session.execute(text("""
                SELECT vsi.identity_zh, vdr.singapore_identity_id
                FROM visa_documents_request vdr
                LEFT JOIN visa_singapore_identity vsi ON vdr.singapore_identity_id = vsi.id
                WHERE vdr.visa_type_id = :visa_type_id
            """), {'visa_type_id': vt.id})
            
            vdr_identities = []
            for row in result.fetchall():
                if row[1] is None:
                    vdr_identities.append('SHARE')
                else:
                    vdr_identities.append(row[0])
            print(f"   visa_documents_request: {vdr_identities}")

if __name__ == "__main__":
    test_visa_identity_consistency() 
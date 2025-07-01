#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复签证身份关联数据
同步 visa_type_identities 表和 VisaDocuments 表的数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App import create_app
from App.models.Visamodels import db, VisaTypes, VisaSingaporeIdentity, VisaDocuments
from sqlalchemy import text

def fix_visa_identity_data():
    """修复签证身份关联数据"""
    app = create_app()
    
    with app.app_context():
        print("🔧 开始修复签证身份关联数据")
        print("=" * 50)
        
        # 获取所有签证类型
        visa_types = VisaTypes.query.all()
        print(f"📋 找到 {len(visa_types)} 个签证类型")
        
        fixed_count = 0
        
        for vt in visa_types:
            print(f"\n🔸 处理签证类型: {vt.visa_type}")
            
            # 获取当前两个表的数据
            current_identities = [identity.identity_zh for identity in vt.identities]
            current_docs = VisaDocuments.query.filter_by(visa_type_id=vt.id).all()
            current_doc_identities = []
            for doc in current_docs:
                if doc.singapore_identity_id:
                    identity = VisaSingaporeIdentity.query.get(doc.singapore_identity_id)
                    if identity:
                        current_doc_identities.append(identity.identity_zh)
                else:
                    current_doc_identities.append('SHARE')
            
            print(f"   当前 visa_type_identities: {current_identities}")
            print(f"   当前 VisaDocuments: {current_doc_identities}")
            
            # 检查是否需要修复
            non_share_doc_identities = [id for id in current_doc_identities if id != 'SHARE']
            if set(current_identities) != set(non_share_doc_identities):
                print(f"   ⚠️  数据不一致，开始修复...")
                
                try:
                    # 1. 清空 visa_type_identities 表
                    vt.identities.clear()
                    
                    # 2. 根据 VisaDocuments 表重新填充 visa_type_identities 表
                    for doc in current_docs:
                        if doc.singapore_identity_id:  # 排除SHARE
                            identity = VisaSingaporeIdentity.query.get(doc.singapore_identity_id)
                            if identity and identity.identity_zh != 'SHARE':
                                vt.identities.append(identity)
                                print(f"      ✅ 添加身份: {identity.identity_zh}")
                    
                    # 3. 提交更改
                    db.session.commit()
                    
                    # 4. 验证修复结果
                    fixed_identities = [identity.identity_zh for identity in vt.identities]
                    print(f"   ✅ 修复完成，新的 visa_type_identities: {fixed_identities}")
                    
                    fixed_count += 1
                    
                except Exception as e:
                    print(f"   ❌ 修复失败: {str(e)}")
                    db.session.rollback()
            else:
                print(f"   ✅ 数据已一致，无需修复")
        
        print(f"\n🎉 修复完成！共修复了 {fixed_count} 个签证类型")
        
        # 最终验证
        print(f"\n🔍 最终验证")
        print("-" * 30)
        
        for vt in visa_types:
            identities = [identity.identity_zh for identity in vt.identities]
            docs = VisaDocuments.query.filter_by(visa_type_id=vt.id).all()
            doc_identities = []
            for doc in docs:
                if doc.singapore_identity_id:
                    identity = VisaSingaporeIdentity.query.get(doc.singapore_identity_id)
                    if identity:
                        doc_identities.append(identity.identity_zh)
                else:
                    doc_identities.append('SHARE')
            
            non_share_doc_identities = [id for id in doc_identities if id != 'SHARE']
            if set(identities) == set(non_share_doc_identities):
                print(f"   ✅ {vt.visa_type}: 数据一致")
            else:
                print(f"   ❌ {vt.visa_type}: 数据仍不一致")
                print(f"      visa_type_identities: {identities}")
                print(f"      VisaDocuments: {non_share_doc_identities}")

if __name__ == "__main__":
    fix_visa_identity_data() 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SHARE配置的保存和读取功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app, db
from App.models import VisaTypes, VisaDocuments, VisaDocumentsList, VisaSingaporeIdentity

def test_share_config():
    """测试SHARE配置功能"""
    app = create_app()
    
    with app.app_context():
        print("=== 测试SHARE配置的保存和读取功能 ===\n")
        
        # 1. 获取测试数据
        visa_type = VisaTypes.query.first()
        if not visa_type:
            print("❌ 没有找到签证类型")
            return
        
        documents = VisaDocumentsList.query.limit(3).all()
        if not documents:
            print("❌ 没有找到文档")
            return
        
        print(f"1. 测试数据:")
        print(f"   签证类型: {visa_type.visa_type} (ID: {visa_type.id})")
        print(f"   文档: {[d.name for d in documents]}")
        
        # 2. 清理现有SHARE配置
        existing_share = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=None
        ).all()
        
        for share in existing_share:
            db.session.delete(share)
        db.session.commit()
        print(f"\n2. 清理了 {len(existing_share)} 个现有SHARE配置")
        
        # 3. 创建SHARE配置
        share_config = VisaDocuments(
            visa_type_id=visa_type.id,
            singapore_identity_id=None,  # SHARE配置
            additional_info="测试SHARE配置"
        )
        share_config.selected_documents = documents[:2]  # 选择前2个文档
        db.session.add(share_config)
        db.session.commit()
        
        print(f"\n3. 创建SHARE配置成功:")
        print(f"   配置ID: {share_config.id}")
        print(f"   选中文档: {[d.name for d in share_config.selected_documents]}")
        
        # 4. 验证保存的数据
        saved_share = VisaDocuments.query.filter_by(
            visa_type_id=visa_type.id,
            singapore_identity_id=None
        ).first()
        
        if saved_share and saved_share.selected_documents:
            print(f"\n4. 验证保存的数据:")
            print(f"   找到SHARE配置: {saved_share.id}")
            print(f"   选中文档数: {len(saved_share.selected_documents)}")
            print(f"   文档列表: {[d.name for d in saved_share.selected_documents]}")
            
            # 5. 模拟API数据获取
            print(f"\n5. 模拟API数据获取:")
            
            # 获取该签证类型的所有文档配置
            visa_documents = VisaDocuments.query.filter_by(visa_type_id=visa_type.id).all()
            
            # 查找SHARE配置
            share_docs = [vd for vd in visa_documents if vd.singapore_identity_id is None]
            
            selected_share_documents = []
            for vd in share_docs:
                if vd.selected_documents:
                    for doc in vd.selected_documents:
                        selected_share_documents.append({
                            'id': doc.id,
                            'name': doc.name,
                            'category': doc.category
                        })
            
            print(f"   找到 {len(share_docs)} 个SHARE配置记录")
            print(f"   选中文档: {[d['name'] for d in selected_share_documents]}")
            print(f"   文档ID: {[d['id'] for d in selected_share_documents]}")
            
            # 6. 清理测试数据
            db.session.delete(saved_share)
            db.session.commit()
            print(f"\n6. 清理测试数据完成")
            
            print(f"\n✅ SHARE配置测试成功！")
            return True
        else:
            print(f"\n❌ SHARE配置验证失败")
            return False

if __name__ == '__main__':
    success = test_share_config()
    if not success:
        sys.exit(1) 
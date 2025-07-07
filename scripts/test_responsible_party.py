#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试responsible_party功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models.Product.Visamodels import VisaDocuments, VisaTypes, VisaSingaporeIdentity, VisaDocumentsList

def test_responsible_party():
    """测试responsible_party功能"""
    
    print("=== 测试responsible_party功能 ===")
    
    app = create_app()
    with app.app_context():
        try:
            # 1. 检查字段是否存在
            print("\n1. 检查visa_document_documents表结构...")
            engine = db.engine
            connection = engine.raw_connection()
            cursor = connection.cursor()
            
            cursor.execute("DESCRIBE visa_document_documents")
            columns = cursor.fetchall()
            
            column_names = [col[0] for col in columns]
            print("字段列表:", column_names)
            
            if 'responsible_party' in column_names:
                print("✅ responsible_party字段存在")
            else:
                print("❌ responsible_party字段不存在")
                return False
            
            # 2. 测试插入数据
            print("\n2. 测试插入数据...")
            
            # 获取一个签证类型
            visa_type = VisaTypes.query.first()
            if not visa_type:
                print("❌ 没有找到签证类型")
                return False
            
            # 获取SHARE身份
            share_identity = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
            if not share_identity:
                print("❌ 没有找到SHARE身份")
                return False
            
            # 获取一些文档
            documents = VisaDocumentsList.query.limit(3).all()
            if not documents:
                print("❌ 没有找到文档")
                return False
            
            # 创建VisaDocuments记录
            visa_doc = VisaDocuments(
                visa_type_id=visa_type.id,
                singapore_identity_id=share_identity.id,
                additional_info='测试补充信息'
            )
            db.session.add(visa_doc)
            db.session.flush()
            
            print(f"✅ 创建VisaDocuments记录，ID: {visa_doc.id}")
            
            # 3. 测试插入关联数据（包含responsible_party）
            print("\n3. 测试插入关联数据...")
            
            for i, doc in enumerate(documents):
                responsible_party = 'FOR_AGENT' if i == 0 else 'FOR_APPLICATION'
                
                sql = """
                    INSERT INTO visa_document_documents (visa_document_id, document_id, responsible_party)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (visa_doc.id, doc.id, responsible_party))
                print(f"✅ 插入关联: 文档'{doc.name}' -> 准备方'{responsible_party}'")
            
            connection.commit()
            
            # 4. 测试查询数据
            print("\n4. 测试查询数据...")
            
            sql = """
                SELECT vdd.document_id, vdd.responsible_party, vdl.name
                FROM visa_document_documents vdd
                JOIN visa_documents_list vdl ON vdd.document_id = vdl.id
                WHERE vdd.visa_document_id = %s
            """
            cursor.execute(sql, (visa_doc.id,))
            results = cursor.fetchall()
            
            print("查询结果:")
            for doc_id, responsible_party, doc_name in results:
                print(f"  - 文档'{doc_name}' (ID: {doc_id}) -> 准备方: {responsible_party}")
            
            # 5. 清理测试数据
            print("\n5. 清理测试数据...")
            
            cursor.execute("DELETE FROM visa_document_documents WHERE visa_document_id = %s", (visa_doc.id,))
            db.session.delete(visa_doc)
            db.session.commit()
            
            print("✅ 测试数据已清理")
            
            cursor.close()
            connection.close()
            
            print("\n✅ responsible_party功能测试完成！")
            return True
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_responsible_party()
    if success:
        print("✅ 所有测试通过！")
    else:
        print("❌ 测试失败！")
        sys.exit(1) 
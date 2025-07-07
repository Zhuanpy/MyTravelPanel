#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试responsible_party字段
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db

def simple_test_responsible_party():
    """简单测试responsible_party字段"""
    
    print("=== 简单测试responsible_party字段 ===")
    
    app = create_app()
    with app.app_context():
        try:
            # 检查字段是否存在
            print("\n1. 检查visa_document_documents表结构...")
            engine = db.engine
            connection = engine.raw_connection()
            cursor = connection.cursor()
            
            cursor.execute("DESCRIBE visa_document_documents")
            columns = cursor.fetchall()
            
            print("表结构:")
            for col in columns:
                print(f"  {col[0]} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
            
            column_names = [col[0] for col in columns]
            if 'responsible_party' in column_names:
                print("✅ responsible_party字段存在")
            else:
                print("❌ responsible_party字段不存在")
                return False
            
            # 检查现有数据
            print("\n2. 检查现有数据...")
            cursor.execute("SELECT COUNT(*) FROM visa_document_documents")
            count = cursor.fetchone()[0]
            print(f"现有关联记录数: {count}")
            
            if count > 0:
                cursor.execute("SELECT visa_document_id, document_id, responsible_party FROM visa_document_documents LIMIT 5")
                results = cursor.fetchall()
                print("示例数据:")
                for visa_doc_id, doc_id, responsible_party in results:
                    print(f"  VisaDocID: {visa_doc_id}, DocID: {doc_id}, 准备方: {responsible_party}")
            
            cursor.close()
            connection.close()
            
            print("\n✅ 简单测试完成！")
            return True
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = simple_test_responsible_party()
    if success:
        print("✅ 测试通过！")
    else:
        print("❌ 测试失败！")
        sys.exit(1) 
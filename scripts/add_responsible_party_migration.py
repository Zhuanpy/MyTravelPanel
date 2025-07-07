#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加responsible_party字段到visa_document_documents表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db

def add_responsible_party_field():
    """添加responsible_party字段到visa_document_documents表"""
    
    print("=== 添加responsible_party字段到visa_document_documents表 ===")
    
    app = create_app()
    with app.app_context():
        # 获取数据库连接
        engine = db.engine
        connection = engine.raw_connection()
        cursor = connection.cursor()
        
        try:
            # 添加responsible_party字段
            sql = "ALTER TABLE visa_document_documents ADD COLUMN responsible_party VARCHAR(20) DEFAULT 'FOR_APPLICATION' COMMENT '资料准备方：FOR_APPLICATION(申请人准备)/FOR_AGENT(旅行社准备)'"
            print(f"执行SQL: {sql}")
            cursor.execute(sql)
            print("✓ responsible_party字段添加成功")
            
            # 提交事务
            connection.commit()
            print("✓ 事务已提交")
            
            # 验证字段是否添加成功
            cursor.execute("DESCRIBE visa_document_documents")
            columns = cursor.fetchall()
            
            print("\n=== visa_document_documents表当前结构 ===")
            column_names = []
            for col in columns:
                column_name = col[0]
                column_names.append(column_name)
                print(f"  {column_name} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
            
            if 'responsible_party' in column_names:
                print("\n✅ responsible_party字段添加成功！")
                return True
            else:
                print("\n❌ responsible_party字段添加失败！")
                return False
                
        except Exception as e:
            if "Duplicate column name" in str(e):
                print(f"⚠ responsible_party字段已存在: {e}")
                return True
            else:
                print(f"✗ 添加字段时发生错误: {e}")
                return False
        finally:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    success = add_responsible_party_field()
    if success:
        print("✅ 操作成功完成！")
    else:
        print("❌ 操作失败！")
        sys.exit(1) 
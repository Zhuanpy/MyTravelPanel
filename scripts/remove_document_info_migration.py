#!/usr/bin/env python3
"""
删除 visa_documents_request 表中的 document_info 字段
因为文档信息现在通过 visa_document_documents 关联表存储
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db

def remove_document_info_field():
    """删除 document_info 字段"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始删除 document_info 字段...")
            
            # 检查字段是否存在
            result = db.session.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'visa_documents_request' 
                AND COLUMN_NAME = 'document_info'
                AND TABLE_SCHEMA = DATABASE()
            """).fetchone()
            
            if result:
                print("✅ 找到 document_info 字段，准备删除...")
                
                # 删除字段
                db.session.execute("ALTER TABLE `visa_documents_request` DROP COLUMN `document_info`")
                db.session.commit()
                
                print("✅ document_info 字段删除成功")
            else:
                print("ℹ️ document_info 字段不存在，无需删除")
            
            # 验证字段已删除
            result = db.session.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'visa_documents_request' 
                AND COLUMN_NAME = 'document_info'
                AND TABLE_SCHEMA = DATABASE()
            """).fetchone()
            
            if not result:
                print("✅ 验证成功：document_info 字段已删除")
            else:
                print("❌ 验证失败：document_info 字段仍然存在")
                return False
            
            # 显示当前表结构
            print("\n📋 当前 visa_documents_request 表结构：")
            columns = db.session.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'visa_documents_request' 
                AND TABLE_SCHEMA = DATABASE()
                ORDER BY ORDINAL_POSITION
            """).fetchall()
            
            for col in columns:
                print(f"  - {col[0]} ({col[1]}, {'NULL' if col[2] == 'YES' else 'NOT NULL'})")
            
            return True
            
        except Exception as e:
            print(f"❌ 删除字段时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = remove_document_info_field()
    if success:
        print("\n🎉 迁移完成！document_info 字段已成功删除")
        print("📝 现在所有文档信息都通过 visa_document_documents 关联表存储")
    else:
        print("\n❌ 迁移失败！请检查错误信息")
        sys.exit(1) 
#!/usr/bin/env python3
"""
执行联系人字段迁移脚本
"""

import sys
import os
import pymysql
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from App.config import Config

def execute_migration():
    """执行数据库迁移"""
    try:
        # 连接数据库
        connection = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("数据库连接成功")
        
        with connection.cursor() as cursor:
            # 检查字段是否已存在
            cursor.execute("DESCRIBE project_refs")
            columns = [column['Field'] for column in cursor.fetchall()]
            
            # 添加联系人姓名字段
            if 'contact_name' not in columns:
                print("添加 contact_name 字段...")
                cursor.execute("""
                    ALTER TABLE `project_refs` 
                    ADD COLUMN `contact_name` VARCHAR(50) NULL COMMENT '联系人姓名' AFTER `supplier_phone`
                """)
                print("✓ contact_name 字段添加成功")
            else:
                print("✓ contact_name 字段已存在")
            
            # 添加联系电话字段
            if 'contact_phone' not in columns:
                print("添加 contact_phone 字段...")
                cursor.execute("""
                    ALTER TABLE `project_refs` 
                    ADD COLUMN `contact_phone` VARCHAR(20) NULL COMMENT '联系电话' AFTER `contact_name`
                """)
                print("✓ contact_phone 字段添加成功")
            else:
                print("✓ contact_phone 字段已存在")
            
            # 添加电子邮箱字段
            if 'contact_email' not in columns:
                print("添加 contact_email 字段...")
                cursor.execute("""
                    ALTER TABLE `project_refs` 
                    ADD COLUMN `contact_email` VARCHAR(100) NULL COMMENT '电子邮箱' AFTER `contact_phone`
                """)
                print("✓ contact_email 字段添加成功")
            else:
                print("✓ contact_email 字段已存在")
            
            # 提交事务
            connection.commit()
            print("✓ 所有字段迁移完成")
            
            # 验证字段是否添加成功
            cursor.execute("DESCRIBE project_refs")
            final_columns = [column['Field'] for column in cursor.fetchall()]
            print(f"当前表字段: {', '.join(final_columns)}")
            
    except Exception as e:
        print(f"迁移失败: {e}")
        if 'connection' in locals():
            connection.rollback()
        return False
    finally:
        if 'connection' in locals():
            connection.close()
    
    return True

if __name__ == "__main__":
    print("开始执行联系人字段迁移...")
    success = execute_migration()
    if success:
        print("✓ 迁移执行成功")
    else:
        print("✗ 迁移执行失败")
        sys.exit(1) 
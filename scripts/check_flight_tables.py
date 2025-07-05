#!/usr/bin/env python3
"""
检查机票相关表结构的脚本
"""

import sys
import os
import pymysql
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from App.config import Config

def check_flight_tables():
    """检查机票相关表结构"""
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
            # 检查 project_flight_passengers 表结构
            print("\n=== 检查 project_flight_passengers 表结构 ===")
            cursor.execute("DESCRIBE project_flight_passengers")
            columns = cursor.fetchall()
            
            if not columns:
                print("❌ project_flight_passengers 表不存在")
                return False
            
            print("当前字段:")
            for column in columns:
                print(f"  - {column['Field']}: {column['Type']} {column['Null']} {column['Key']} {column['Default']} {column['Extra']}")
            
            # 检查是否有 ref_id 字段
            ref_id_exists = any(col['Field'] == 'ref_id' for col in columns)
            if not ref_id_exists:
                print("\n❌ 缺少 ref_id 字段")
                return False
            else:
                print("\n✅ ref_id 字段存在")
            
            # 检查 project_flight_segments 表结构
            print("\n=== 检查 project_flight_segments 表结构 ===")
            cursor.execute("DESCRIBE project_flight_segments")
            segments_columns = cursor.fetchall()
            
            if not segments_columns:
                print("❌ project_flight_segments 表不存在")
                return False
            
            print("当前字段:")
            for column in segments_columns:
                print(f"  - {column['Field']}: {column['Type']} {column['Null']} {column['Key']} {column['Default']} {column['Extra']}")
            
            # 检查是否有 ref_id 字段
            segments_ref_id_exists = any(col['Field'] == 'ref_id' for col in segments_columns)
            if not segments_ref_id_exists:
                print("\n❌ project_flight_segments 表缺少 ref_id 字段")
                return False
            else:
                print("\n✅ project_flight_segments 表的 ref_id 字段存在")
            
            # 检查外键约束
            print("\n=== 检查外键约束 ===")
            cursor.execute("""
                SELECT 
                    CONSTRAINT_NAME,
                    TABLE_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME IN ('project_flight_passengers', 'project_flight_segments')
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (Config.DB_NAME,))
            
            foreign_keys = cursor.fetchall()
            if foreign_keys:
                print("外键约束:")
                for fk in foreign_keys:
                    print(f"  - {fk['CONSTRAINT_NAME']}: {fk['TABLE_NAME']}.{fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}")
            else:
                print("❌ 没有找到外键约束")
            
    except Exception as e:
        print(f"检查失败: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.close()
    
    return True

if __name__ == "__main__":
    print("开始检查机票相关表结构...")
    success = check_flight_tables()
    if success:
        print("\n✅ 表结构检查完成")
    else:
        print("\n❌ 表结构检查失败")
        sys.exit(1) 
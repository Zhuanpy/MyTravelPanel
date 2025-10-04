#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加员工等级字段
"""

import sqlite3
import sys
import os

def migrate_database():
    """执行数据库迁移"""
    db_path = 'instance/travel_panel_new.db'
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(user_profiles)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'staff_level' in columns:
            print("字段 staff_level 已存在，跳过迁移")
            return True
        
        # 添加字段
        print("添加 staff_level 字段...")
        cursor.execute("""
            ALTER TABLE user_profiles 
            ADD COLUMN staff_level INTEGER DEFAULT 1
        """)
        
        # 创建索引
        print("创建索引...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_profiles_staff_level 
            ON user_profiles(staff_level)
        """)
        
        # 提交更改
        conn.commit()
        print("数据库迁移成功完成！")
        
        # 验证字段添加
        cursor.execute("PRAGMA table_info(user_profiles)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'staff_level' in columns:
            print("验证成功：staff_level 字段已添加")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"迁移失败: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)

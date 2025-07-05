#!/usr/bin/env python3
"""
添加 leader_name 字段到 project_headers 表的迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from sqlalchemy import text

def add_leader_name_column():
    """添加 leader_name 字段到 project_headers 表"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'project_headers' 
                AND COLUMN_NAME = 'leader_name'
            """))
            
            if result.fetchone():
                print("✅ leader_name 字段已存在，跳过迁移")
                return
            
            # 添加 leader_name 字段
            db.session.execute(text("""
                ALTER TABLE project_headers 
                ADD COLUMN leader_name VARCHAR(100) NULL
            """))
            
            db.session.commit()
            print("✅ 成功添加 leader_name 字段到 project_headers 表")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 迁移失败: {str(e)}")
            raise

def test_leader_name_field():
    """测试 leader_name 字段功能"""
    app = create_app()
    
    with app.app_context():
        try:
            # 测试查询
            result = db.session.execute(text("""
                SELECT id, hid, staff_name, leader_name 
                FROM project_headers 
                LIMIT 5
            """))
            
            rows = result.fetchall()
            print("\n=== 测试 leader_name 字段 ===")
            print("当前项目数据:")
            for row in rows:
                print(f"  ID: {row[0]}, HID: {row[1]}, 经办人: {row[2]}, 负责人: {row[3] or '未设置'}")
            
            print("\n✅ leader_name 字段测试成功")
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            raise

if __name__ == "__main__":
    print("开始迁移 leader_name 字段...")
    add_leader_name_column()
    test_leader_name_field()
    print("\n🎉 迁移完成！") 
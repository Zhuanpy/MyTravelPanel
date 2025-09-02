#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复Todo模型外键问题的脚本
将todos表的user_id外键从users.id改为auth_users.id
"""

import os
import sys
from sqlalchemy import text

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from App_new import create_app
from App_new.exts import db

def fix_todo_foreign_key():
    """修复Todo表的外键约束"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查todos表是否存在
            result = db.session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='todos'
            """)).fetchone()
            
            if not result:
                print("todos表不存在，无需修复")
                return
            
            # 检查auth_users表是否存在
            result = db.session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='auth_users'
            """)).fetchone()
            
            if not result:
                print("auth_users表不存在，请先创建用户表")
                return
            
            # 检查当前外键约束
            result = db.session.execute(text("""
                PRAGMA foreign_key_list(todos)
            """)).fetchall()
            
            print("当前todos表的外键约束:")
            for row in result:
                print(f"  {row}")
            
            # 删除现有的外键约束（如果存在）
            try:
                # 在SQLite中，我们需要重新创建表来修改外键
                print("开始修复外键约束...")
                
                # 1. 创建新的todos表结构
                db.session.execute(text("""
                    CREATE TABLE todos_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        is_completed BOOLEAN DEFAULT 0,
                        due_date DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        priority INTEGER DEFAULT 2,
                        user_id INTEGER REFERENCES auth_users(id)
                    )
                """))
                
                # 2. 复制数据
                db.session.execute(text("""
                    INSERT INTO todos_new 
                    SELECT * FROM todos
                """))
                
                # 3. 删除旧表
                db.session.execute(text("DROP TABLE todos"))
                
                # 4. 重命名新表
                db.session.execute(text("ALTER TABLE todos_new RENAME TO todos"))
                
                # 5. 重新创建索引
                db.session.execute(text("""
                    CREATE INDEX ix_todos_user_id ON todos(user_id)
                """))
                
                db.session.commit()
                print("✅ 外键约束修复成功！")
                
                # 验证修复结果
                result = db.session.execute(text("""
                    PRAGMA foreign_key_list(todos)
                """)).fetchall()
                
                print("修复后的todos表外键约束:")
                for row in result:
                    print(f"  {row}")
                    
            except Exception as e:
                db.session.rollback()
                print(f"❌ 修复失败: {str(e)}")
                raise
                
        except Exception as e:
            print(f"❌ 执行过程中出错: {str(e)}")
            raise

if __name__ == "__main__":
    fix_todo_foreign_key()

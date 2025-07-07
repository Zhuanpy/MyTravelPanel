#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单独添加duration_days字段
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db

def add_duration_days_field():
    """添加duration_days字段"""
    
    print("=== 添加duration_days字段 ===")
    
    app = create_app()
    with app.app_context():
        # 获取数据库连接
        engine = db.engine
        connection = engine.raw_connection()
        cursor = connection.cursor()
        
        try:
            # 添加duration_days字段
            sql = "ALTER TABLE travelproducts ADD COLUMN duration_days INT NULL COMMENT '行程天数'"
            print(f"执行SQL: {sql}")
            cursor.execute(sql)
            print("✓ duration_days字段添加成功")
            
            # 提交事务
            connection.commit()
            print("✓ 事务已提交")
            
            # 验证字段是否添加成功
            cursor.execute("DESCRIBE travelproducts")
            columns = cursor.fetchall()
            
            print("\n=== travelproducts表当前结构 ===")
            column_names = []
            for col in columns:
                column_name = col[0]
                column_names.append(column_name)
                print(f"  {column_name} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
            
            if 'duration_days' in column_names:
                print("\n✅ duration_days字段添加成功！")
                return True
            else:
                print("\n❌ duration_days字段添加失败！")
                return False
                
        except Exception as e:
            if "Duplicate column name" in str(e):
                print(f"⚠ duration_days字段已存在: {e}")
                return True
            else:
                print(f"✗ 添加字段时发生错误: {e}")
                return False
        finally:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    success = add_duration_days_field()
    if success:
        print("✅ 操作成功完成！")
    else:
        print("❌ 操作失败！")
        sys.exit(1) 
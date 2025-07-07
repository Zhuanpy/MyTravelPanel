#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行缺失字段的添加
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db

def add_missing_fields():
    """添加缺失的字段"""
    
    print("=== 开始添加缺失的字段 ===")
    
    # 读取SQL文件
    sql_file_path = os.path.join(os.path.dirname(__file__), 'add_missing_product_fields.sql')
    
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("SQL文件读取成功")
        
        # 分割SQL语句
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        # 获取数据库连接
        app = create_app()
        with app.app_context():
            # 获取数据库连接
            engine = db.engine
            connection = engine.raw_connection()
            cursor = connection.cursor()
            
            print(f"数据库连接成功，准备执行 {len(sql_statements)} 条SQL语句")
            
            # 执行每条SQL语句
            for i, sql in enumerate(sql_statements, 1):
                if sql.startswith('--') or not sql.strip():
                    continue
                    
                try:
                    print(f"执行第 {i} 条SQL: {sql[:50]}...")
                    cursor.execute(sql)
                    print(f"✓ 第 {i} 条SQL执行成功")
                except Exception as e:
                    if "Duplicate column name" in str(e):
                        print(f"⚠ 第 {i} 条SQL跳过（字段已存在）: {e}")
                    else:
                        print(f"✗ 第 {i} 条SQL执行失败: {e}")
                        raise
            
            # 提交事务
            connection.commit()
            print("✓ 所有SQL语句执行完成，事务已提交")
            
            # 验证表结构
            cursor.execute("DESCRIBE travelproducts")
            columns = cursor.fetchall()
            print("\n=== travelproducts表当前结构 ===")
            for col in columns:
                print(f"  {col[0]} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
            
            cursor.close()
            connection.close()
            
    except FileNotFoundError:
        print(f"✗ SQL文件未找到: {sql_file_path}")
        return False
    except Exception as e:
        print(f"✗ 迁移过程中发生错误: {e}")
        return False
    
    print("=== 缺失字段添加完成 ===")
    return True

if __name__ == "__main__":
    success = add_missing_fields()
    if success:
        print("✅ 字段添加成功完成！")
    else:
        print("❌ 字段添加失败！")
        sys.exit(1) 
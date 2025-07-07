#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查travelproducts表的字段
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db

def check_product_fields():
    """检查travelproducts表的字段"""
    
    print("=== 检查travelproducts表字段 ===")
    
    app = create_app()
    with app.app_context():
        # 获取数据库连接
        engine = db.engine
        connection = engine.raw_connection()
        cursor = connection.cursor()
        
        # 检查表结构
        cursor.execute("DESCRIBE travelproducts")
        columns = cursor.fetchall()
        
        print("=== travelproducts表当前结构 ===")
        column_names = []
        for col in columns:
            column_name = col[0]
            column_names.append(column_name)
            print(f"  {column_name} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
        
        # 检查特定字段是否存在
        print("\n=== 检查特定字段 ===")
        required_fields = ['product_type', 'duration_days']
        
        for field in required_fields:
            if field in column_names:
                print(f"✓ {field} 字段存在")
            else:
                print(f"✗ {field} 字段不存在")
        
        cursor.close()
        connection.close()
        
        return all(field in column_names for field in required_fields)

if __name__ == "__main__":
    success = check_product_fields()
    if success:
        print("\n✅ 所有必需字段都存在！")
    else:
        print("\n❌ 缺少必需字段！")
        sys.exit(1) 
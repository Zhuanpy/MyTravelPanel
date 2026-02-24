# -*- coding: utf-8 -*-
"""
给 products_unified 表添加 product_name_en（英文产品名称）字段
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    sql = """
    ALTER TABLE products_unified
    ADD COLUMN product_name_en VARCHAR(200) NULL COMMENT '产品名称（英文）'
    AFTER product_name
    """
    try:
        db.session.execute(db.text(sql))
        db.session.commit()
        print("成功添加 product_name_en 字段")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate column' in str(e):
            print("字段已存在，跳过")
        else:
            print(f"错误: {e}")

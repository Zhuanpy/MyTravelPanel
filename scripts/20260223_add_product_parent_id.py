# -*- coding: utf-8 -*-
"""
给 products_unified 表添加 parent_id（父产品ID）字段，支持产品变体/分类
例如：环球影城（主产品） → 普通门票、快捷通道门票（子产品）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    # 添加 parent_id 字段
    sql_add_column = """
    ALTER TABLE products_unified
    ADD COLUMN parent_id INT NULL COMMENT '父产品ID，NULL表示主产品'
    AFTER valid_until
    """

    # 添加外键约束
    sql_add_fk = """
    ALTER TABLE products_unified
    ADD CONSTRAINT fk_product_parent
    FOREIGN KEY (parent_id) REFERENCES products_unified(id)
    ON DELETE SET NULL
    """

    # 添加索引
    sql_add_index = """
    ALTER TABLE products_unified
    ADD INDEX idx_parent_id (parent_id)
    """

    try:
        db.session.execute(db.text(sql_add_column))
        db.session.commit()
        print("成功添加 parent_id 字段")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate column' in str(e):
            print("parent_id 字段已存在，跳过")
        else:
            print(f"添加字段错误: {e}")
            sys.exit(1)

    try:
        db.session.execute(db.text(sql_add_fk))
        db.session.commit()
        print("成功添加外键约束")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate' in str(e) or 'already exists' in str(e):
            print("外键约束已存在，跳过")
        else:
            print(f"添加外键警告: {e}")

    try:
        db.session.execute(db.text(sql_add_index))
        db.session.commit()
        print("成功添加索引")
    except Exception as e:
        db.session.rollback()
        if 'Duplicate' in str(e) or 'already exists' in str(e):
            print("索引已存在，跳过")
        else:
            print(f"添加索引警告: {e}")

    print("迁移完成")

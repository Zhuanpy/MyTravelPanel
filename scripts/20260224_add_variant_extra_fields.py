# -*- coding: utf-8 -*-
"""
为 products_ticket_variant 表添加 delivery_type, includes, excludes, important_notes 字段
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from App_new import create_app
from App_new.exts import db

app = create_app()

with app.app_context():
    conn = db.engine.connect()

    # 检查字段是否已存在
    result = conn.execute(db.text("SHOW COLUMNS FROM products_ticket_variant LIKE 'delivery_type'"))
    if result.fetchone():
        print('字段已存在，跳过迁移')
    else:
        print('开始添加字段...')
        conn.execute(db.text("""
            ALTER TABLE products_ticket_variant
            ADD COLUMN delivery_type VARCHAR(20) DEFAULT 'e_ticket' COMMENT '取票方式' AFTER is_active,
            ADD COLUMN includes TEXT COMMENT '费用包含' AFTER delivery_type,
            ADD COLUMN excludes TEXT COMMENT '费用不含' AFTER includes,
            ADD COLUMN important_notes TEXT COMMENT '重要提示' AFTER excludes
        """))
        conn.commit()
        print('字段添加成功：delivery_type, includes, excludes, important_notes')

    conn.close()
    print('迁移完成')

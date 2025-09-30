# -*- coding: utf-8 -*-
"""
添加公司点击次数字段
"""

from flask_migrate import Migrate
from App_new.exts import db
from sqlalchemy import text

def upgrade():
    """添加点击次数字段"""
    try:
        # 添加点击次数字段
        db.session.execute(text("""
            ALTER TABLE customer_companies 
            ADD COLUMN click_count INT DEFAULT 0 COMMENT '点击次数'
        """))
        
        # 添加最后点击时间字段
        db.session.execute(text("""
            ALTER TABLE customer_companies 
            ADD COLUMN last_clicked_at DATETIME NULL COMMENT '最后点击时间'
        """))
        
        db.session.commit()
        print("✅ 成功添加公司点击次数字段")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 添加字段失败: {e}")
        raise

def downgrade():
    """移除点击次数字段"""
    try:
        # 移除字段
        db.session.execute(text("""
            ALTER TABLE customer_companies 
            DROP COLUMN click_count
        """))
        
        db.session.execute(text("""
            ALTER TABLE customer_companies 
            DROP COLUMN last_clicked_at
        """))
        
        db.session.commit()
        print("✅ 成功移除公司点击次数字段")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 移除字段失败: {e}")
        raise

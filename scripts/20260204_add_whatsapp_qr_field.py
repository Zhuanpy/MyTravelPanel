# -*- coding: utf-8 -*-
"""
添加 whatsapp_qr 字段到 user_profiles 表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text

app = create_app()

def run_migration():
    with app.app_context():
        # 检查并添加 whatsapp_qr 字段
        try:
            db.session.execute(text("SELECT whatsapp_qr FROM user_profiles LIMIT 1"))
            print("whatsapp_qr 字段已存在")
        except:
            db.session.rollback()
            db.session.execute(text("ALTER TABLE user_profiles ADD COLUMN whatsapp_qr VARCHAR(255) COMMENT 'WhatsApp二维码图片路径'"))
            db.session.commit()
            print("已添加 whatsapp_qr 字段")

        print("\n迁移完成!")

if __name__ == '__main__':
    run_migration()

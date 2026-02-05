# -*- coding: utf-8 -*-
"""
添加员工联系方式字段到 user_profiles 表
- wechat_id: 微信号
- wechat_qr: 微信二维码图片路径
- whatsapp: WhatsApp号码
- is_public: 是否在联系页面公开显示
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
        # 检查并添加 wechat_id 字段
        try:
            db.session.execute(text("SELECT wechat_id FROM user_profiles LIMIT 1"))
            print("wechat_id 字段已存在")
        except:
            db.session.rollback()
            db.session.execute(text("ALTER TABLE user_profiles ADD COLUMN wechat_id VARCHAR(50)"))
            db.session.commit()
            print("已添加 wechat_id 字段")

        # 检查并添加 wechat_qr 字段
        try:
            db.session.execute(text("SELECT wechat_qr FROM user_profiles LIMIT 1"))
            print("wechat_qr 字段已存在")
        except:
            db.session.rollback()
            db.session.execute(text("ALTER TABLE user_profiles ADD COLUMN wechat_qr VARCHAR(255)"))
            db.session.commit()
            print("已添加 wechat_qr 字段")

        # 检查并添加 whatsapp 字段
        try:
            db.session.execute(text("SELECT whatsapp FROM user_profiles LIMIT 1"))
            print("whatsapp 字段已存在")
        except:
            db.session.rollback()
            db.session.execute(text("ALTER TABLE user_profiles ADD COLUMN whatsapp VARCHAR(20)"))
            db.session.commit()
            print("已添加 whatsapp 字段")

        # 检查并添加 is_public 字段
        try:
            db.session.execute(text("SELECT is_public FROM user_profiles LIMIT 1"))
            print("is_public 字段已存在")
        except:
            db.session.rollback()
            db.session.execute(text("ALTER TABLE user_profiles ADD COLUMN is_public BOOLEAN DEFAULT FALSE"))
            db.session.commit()
            print("已添加 is_public 字段")

        print("\n迁移完成!")
        print("提示: 要在联系页面显示员工，需要在后台将员工的 is_public 设置为 True")

if __name__ == '__main__':
    run_migration()

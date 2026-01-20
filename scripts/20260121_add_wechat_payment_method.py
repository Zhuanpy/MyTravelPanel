# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加 WeChat 付款方式
- project_receipts 表的 payment_method 枚举添加 'wechat' 选项

运行方式: python scripts/20260121_add_wechat_payment_method.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import text


def main():
    print("=" * 60)
    print("数据库迁移：添加 WeChat 付款方式")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        try:
            # 修改 project_receipts 表的 payment_method 枚举
            print("\n1. 修改 project_receipts 表的 payment_method 枚举...")

            alter_sql = text("""
                ALTER TABLE project_receipts
                MODIFY COLUMN payment_method
                ENUM('cash', 'bank_transfer', 'credit_card', 'cheque', 'wechat', 'other')
                NOT NULL COMMENT '付款方式'
            """)

            db.session.execute(alter_sql)
            db.session.commit()
            print("  + 成功添加 'wechat' 到 payment_method 枚举")

            print("\n" + "=" * 60)
            print("迁移完成！")
            print("=" * 60)

        except Exception as e:
            db.session.rollback()
            print(f"\n错误：迁移失败 - {str(e)}")
            raise


if __name__ == '__main__':
    main()

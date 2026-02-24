"""
创建购物车表 member_cart_items
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App_new import create_app
from App_new.exts import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    if 'member_cart_items' in existing_tables:
        print('表 member_cart_items 已存在，跳过创建')
    else:
        # 导入模型确保注册
        from App_new.member.models.cart import CartItem
        CartItem.__table__.create(db.engine)
        print('表 member_cart_items 创建成功')

    print('完成')
